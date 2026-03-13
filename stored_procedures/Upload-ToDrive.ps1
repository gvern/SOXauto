<#
.SYNOPSIS
    Upload a file to Google Drive using a Service Account JSON file
.DESCRIPTION
    Generates a JWT assertion from a service account private key, exchanges it for
    an OAuth access token, and uploads a file to Google Drive (multipart upload).
.PARAMETER FilePath
    Full path to the file to upload.
.PARAMETER FolderId
    Google Drive folder ID where the file will be uploaded.
.PARAMETER FileName
    Optional filename override in Google Drive.
.PARAMETER ServiceAccountJsonPath
    Full path to service account JSON file (contains private key and client email).
.PARAMETER DeleteAfterUpload
    Delete local file after successful upload.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$FilePath,

    [Parameter(Mandatory = $true)]
    [string]$FolderId,

    [Parameter(Mandatory = $false)]
    [string]$FileName,

    [Parameter(Mandatory = $true)]
    [string]$ServiceAccountJsonPath,

    [Parameter(Mandatory = $false)]
    [bool]$DeleteAfterUpload = $true
)

function ConvertTo-Base64Url {
    param([byte[]]$Bytes)

    $base64 = [Convert]::ToBase64String($Bytes)
    return $base64.Replace('+', '-').Replace('/', '_').TrimEnd('=')
}

function Get-ServiceAccount {
    param([string]$JsonPath)

    if (-not (Test-Path -LiteralPath $JsonPath)) {
        throw "Service account file not found: $JsonPath"
    }

    $raw = Get-Content -LiteralPath $JsonPath -Raw
    $obj = $raw | ConvertFrom-Json

    if (-not $obj.client_email -or -not $obj.private_key -or -not $obj.token_uri) {
        throw "Invalid service account JSON. Required fields: client_email, private_key, token_uri"
    }

    return @{
        client_email = [string]$obj.client_email
        private_key = [string]$obj.private_key
        token_uri = [string]$obj.token_uri
    }
}

function Get-GoogleAccessToken {
    param([hashtable]$ServiceAccount)

    $headerJson = @{ alg = 'RS256'; typ = 'JWT' } | ConvertTo-Json -Compress
    $headerBase64 = ConvertTo-Base64Url ([System.Text.Encoding]::UTF8.GetBytes($headerJson))

    $now = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $claimsJson = @{
        iss = $ServiceAccount.client_email
        scope = 'https://www.googleapis.com/auth/drive.file'
        aud = $ServiceAccount.token_uri
        iat = $now
        exp = $now + 3600
    } | ConvertTo-Json -Compress
    $claimsBase64 = ConvertTo-Base64Url ([System.Text.Encoding]::UTF8.GetBytes($claimsJson))

    $signatureInput = "$headerBase64.$claimsBase64"

    $privateKeyPem = $ServiceAccount.private_key
    $privateKeyPem = $privateKeyPem -replace '-----BEGIN PRIVATE KEY-----', ''
    $privateKeyPem = $privateKeyPem -replace '-----END PRIVATE KEY-----', ''
    $privateKeyPem = $privateKeyPem -replace '\\n', "`n"
    $privateKeyPem = $privateKeyPem -replace '\s', ''
    $privateKeyBytes = [Convert]::FromBase64String($privateKeyPem)

    $rsa = [System.Security.Cryptography.RSA]::Create()
    $nullRef = 0
    $rsa.ImportPkcs8PrivateKey($privateKeyBytes, [ref]$nullRef)

    $signatureBytes = $rsa.SignData(
        [System.Text.Encoding]::UTF8.GetBytes($signatureInput),
        [System.Security.Cryptography.HashAlgorithmName]::SHA256,
        [System.Security.Cryptography.RSASignaturePadding]::Pkcs1
    )
    $signatureBase64 = ConvertTo-Base64Url $signatureBytes

    $jwt = "$signatureInput.$signatureBase64"

    $tokenResponse = Invoke-RestMethod -Uri $ServiceAccount.token_uri -Method Post -Body @{
        grant_type = 'urn:ietf:params:oauth:grant-type:jwt-bearer'
        assertion = $jwt
    } -ContentType 'application/x-www-form-urlencoded'

    return $tokenResponse.access_token
}

function Upload-ToGoogleDrive {
    param(
        [string]$AccessToken,
        [string]$UploadFilePath,
        [string]$UploadFolderId,
        [string]$UploadFileName
    )

    if (-not $UploadFileName) {
        $UploadFileName = [System.IO.Path]::GetFileName($UploadFilePath)
    }

    $extension = [System.IO.Path]::GetExtension($UploadFilePath).ToLowerInvariant()
    $mimeType = switch ($extension) {
        '.csv'  { 'text/csv' }
        '.json' { 'application/json' }
        '.xlsx' { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }
        '.pdf'  { 'application/pdf' }
        default { 'application/octet-stream' }
    }

    $metadata = @{ name = $UploadFileName; parents = @($UploadFolderId) } | ConvertTo-Json -Compress
    $fileContent = [System.IO.File]::ReadAllBytes($UploadFilePath)

    $boundary = [Guid]::NewGuid().ToString()
    $lf = "`r`n"

    $bodyLines = @(
        "--$boundary",
        'Content-Type: application/json; charset=UTF-8',
        '',
        $metadata,
        "--$boundary",
        "Content-Type: $mimeType",
        '',
        ''
    )

    $bodyStart = [System.Text.Encoding]::UTF8.GetBytes(($bodyLines -join $lf))
    $bodyEnd = [System.Text.Encoding]::UTF8.GetBytes("$lf--$boundary--$lf")

    $body = New-Object byte[] ($bodyStart.Length + $fileContent.Length + $bodyEnd.Length)
    [System.Buffer]::BlockCopy($bodyStart, 0, $body, 0, $bodyStart.Length)
    [System.Buffer]::BlockCopy($fileContent, 0, $body, $bodyStart.Length, $fileContent.Length)
    [System.Buffer]::BlockCopy($bodyEnd, 0, $body, $bodyStart.Length + $fileContent.Length, $bodyEnd.Length)

    $uploadUri = 'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink'

    return Invoke-RestMethod -Uri $uploadUri -Method Post -Headers @{ Authorization = "Bearer $AccessToken" } -ContentType "multipart/related; boundary=$boundary" -Body $body
}

$result = @{
    status = 'error'
    file_id = $null
    file_name = $null
    web_view_link = $null
    error_message = $null
}

try {
    if (-not (Test-Path -LiteralPath $FilePath)) {
        throw "File not found: $FilePath"
    }

    $serviceAccount = Get-ServiceAccount -JsonPath $ServiceAccountJsonPath
    $accessToken = Get-GoogleAccessToken -ServiceAccount $serviceAccount
    $uploadResult = Upload-ToGoogleDrive -AccessToken $accessToken -UploadFilePath $FilePath -UploadFolderId $FolderId -UploadFileName $FileName

    $result.status = 'success'
    $result.file_id = $uploadResult.id
    $result.file_name = $uploadResult.name
    $result.web_view_link = $uploadResult.webViewLink

    if ($DeleteAfterUpload) {
        Remove-Item -LiteralPath $FilePath -Force
    }
}
catch {
    $result.status = 'error'
    $result.error_message = $_.Exception.Message
}

$result | ConvertTo-Json -Compress
