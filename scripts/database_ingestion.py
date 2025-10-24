import os
import pprint
import pathlib
import argparse
import logging
from typing import Dict, List
from multiprocessing.pool import ThreadPool
import pyspark.sql.functions as F
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col
from src.common import setup_logging
from src.common.aws.ssm import ssm_get_parameter
from src.common.aws.glue import glue_get_table_spec
from src.common.iceberg.iceberg_writer import IcebergWriter
from src.common.config.structured_config import ConfigLoader
from src.common.spark_session_builder import SparkSessionBuilder
from src.common.spark.schema_builders import _build_sql_to_spark_type_map
from src.ingestion_helper import validate_params, read_sql, build_query_list
from src.common.optimizer.file_optimizer import estimate_dataframe_size,determine_optimal_file_size,choose_optimization_strategy,extract_target_file_size


logger = logging.getLogger(__name__)


ENTITY_CONFIG_PATH = "configs/entities"
CONNECTION_CONFIG_PATH = "configs"

def _get_spark_options(connection_config: Dict, connection_type: str):
    spark_options = {}
    if connection_type == "mysql":
        spark_options = {
            "url": connection_config.url,
            "user": connection_config.user,
            "password": connection_config.password,
            "driver": connection_config.driver,
        }
    elif connection_type == "sql_server":
        spark_options = {
            "url": connection_config.url,
            "username": connection_config.username,
            "password": connection_config.password,
            "driver": connection_config.driver,
        }
    elif connection_type == "postgresql":
        spark_options = {
            "url": connection_config.url,
            "user": connection_config.user,
            "password": connection_config.password,
            "driver": connection_config.driver,
        }
    elif connection_type == "mariadb":
        spark_options = {
            "url": connection_config.url,
            "user": connection_config.user,
            "password": connection_config.password,
            "driver": connection_config.driver,
        }
    return spark_options


def excecute_spark_sql(
    spark: SparkSession,
    query_list: List[str],
    entity_config: Dict,
    connection_type: str,
) -> DataFrame:

    # Config output
    catalog: str = entity_config.catalog
    database: str = entity_config.database
    table: str = entity_config.table_name

    logger.info(f"Output table name: {catalog}.{database}.{table}.")

    for obj in query_list:
        query = obj["query"]
        spark_options = _get_spark_options(obj["connection_config"], connection_type)

        if entity_config.query_timeout:
            spark_options["query_timeout"] = entity_config.query_timeout

        query = "({0}) as t".format(query)
        pprint.pprint(query)
        spark_options["dbtable"] = query

        # Write to iceberg
        try:
            logger.info(f"Getting TableSpec for {catalog}.{database}.{table}.")
            table_spec = glue_get_table_spec(db_name=database, table_name=table)
            logger.info(f"Collected TableSpec for {catalog}.{database}.{table}.")
            logger.info(f"Executing query in the source database.")
            df = spark.read.format("jdbc").options(**spark_options).load()
            logger.info(f"Successfully read data.")
            logger.info(f"Transforming data.")
            # apply transformations
            for c in df.columns:
                df = df.withColumn(c, F.translate(c, chr(13), ""))
                df = df.withColumn(c, F.translate(c, chr(10), ""))

            df = (
                df.withColumn("dat_load_timestamp", F.current_timestamp())
                .withColumn("dat_load_date", F.current_date())
                .select([col.name for col in table_spec.columns])
            )
            logger.info(f"Casting datatypes.")
            new_df = df.select(
                [
                    col(cols.name)
                    .cast(_build_sql_to_spark_type_map(spark)[cols.type])
                    .alias(cols.name)
                    for cols in table_spec.columns
                ]
            )
            # ----- FILE SIZE OPTIMIZATION START 
            if getattr(entity_config, 'optimize_file_size', True):
                logger.info(f"Dynamic file size optimization enabled for {catalog}.{database}.{table}")
                
                # Get full table name
                full_table_name = f"{catalog}.{database}.{table}"
                
                # Extract target file size from table if available
                table_target_size_mb, _ = extract_target_file_size(spark, full_table_name)
                
                # Estimate dataframe size
                bytes_per_record, estimated_total_bytes, record_count = estimate_dataframe_size(new_df)
                
                # Determine optimal file size and count
                target_file_size_mb, optimal_file_count = determine_optimal_file_size(
                    estimated_total_bytes, 
                    record_count,
                    table_target_size_mb
                )
                
                # Choose optimization strategy
                strategy, file_count = choose_optimization_strategy(new_df, optimal_file_count)
                
                # Store original coalesce value
                original_coalesce = entity_config.coalesce
                
                # Apply our own coalescing
                logger.info(f"Coalescing DataFrame to {file_count} files (original setting: {original_coalesce or 'None'})")
                optimized_df = new_df.coalesce(file_count)
                
                # Temporarily disable IcebergWriter's coalescing
                entity_config.coalesce = None
                
                logger.info(f"Writing into {catalog}.{database}.{table} with optimized file count ({file_count}).")
                writer = IcebergWriter(
                    entity_config.catalog,
                    entity_config.database,
                    entity_config.table_name,
                    entity_config.coalesce  # This is now None
                )
                writer.write_iceberg(optimized_df, entity_config.write_mode)
                
                # Restore original coalesce value
                entity_config.coalesce = original_coalesce
            else:
                # Original code path without optimization
                logger.info(f"Writing into {catalog}.{database}.{table}.")
                writer = IcebergWriter(
                    entity_config.catalog,
                    entity_config.database,
                    entity_config.table_name,
                    entity_config.coalesce,
                )
                writer.write_iceberg(new_df, entity_config.write_mode)
            # ---- FILE SIZE OPTIMIZATION END ----
            logger.info(f"Successfully written into {catalog}.{database}.{table}.")

        except Exception as e:
            logger.error(f"Error while reading or processing data: {e}.")
            spark.stop()
            raise e

    spark.stop()


def main(entity: str, connection_type: str, config_root_uri: str, spark_config: str):
    # Create Spark session
    logger.info(f"Starting spark session")
    spark_conf_path = f"{config_root_uri}/spark_configs/{spark_config}"
    spark_session_builder = SparkSessionBuilder("database_ingestion", spark_conf_path)
    spark = spark_session_builder.spark
    spark.sql("set spark.sql.legacy.timeParserPolicy=LEGACY")

    # Read config files
    logger.info(f"Reading entity: {entity} config file")
    config_loader = ConfigLoader()

    logger.info(f"Reading entity: {entity} config file")
    entity_config = config_loader.load_entity_config(
        f"{config_root_uri}/{ENTITY_CONFIG_PATH}", entity
    )

    logger.info(f"Validating entity: {entity} params")
    validate_params(entity_config)

    # Read Query
    logger.info(f"Reading query for entity: {entity}")
    query_path = entity_config.query_file
    query = read_sql(f"{config_root_uri}/extract/{connection_type}/{query_path}.sql")

    # Buld quiery list
    logger.info(f"Get query list for entity: {entity}")
    query_list = build_query_list(spark, query, entity_config, connection_type, f"{config_root_uri}/{CONNECTION_CONFIG_PATH}")

    excecute_spark_sql(spark, query_list, entity_config, connection_type)


if __name__ == "__main__":
    setup_logging.root_logger_default_config()

    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--entity", help="the entity for which to run the job")
    parser.add_argument("-c", "--connection", help="type of connection")
    parser.add_argument("-ab", "--artifact-bucket", help="the S3 location of the config files")
    parser.add_argument("-env", "--environment", help="the name of the environment")
    parser.add_argument("-spark_config", "--spark_config", help="name of the spark config yaml file", default="spark_config.yaml")
    args = parser.parse_args()

    # entities: List[str]  = [entity for entity in args.entities.split(',')]
    entity = args.entity
    connection_type = args.connection
    artifact_bucket_name = args.artifact_bucket
    spark_config = args.spark_config
    
    if artifact_bucket_name.startswith('/'):
        config_root_uri = f"{artifact_bucket_name}/ingestion"
    else:
        config_root_uri = f"s3://{artifact_bucket_name}/ingestion"

    env = args.environment
    os.environ["ENV"] = env

    main(entity, connection_type, config_root_uri, spark_config)
    