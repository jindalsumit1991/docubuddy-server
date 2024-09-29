
# docubuddy-server

## Setting up HTTPS with a Self-Signed SSL Certificate in Keycloak

To enable HTTPS in Keycloak, follow these steps to generate and configure a self-signed SSL certificate.

### Step 1: Install OpenSSL
First, ensure you have OpenSSL installed on your system:

**For Ubuntu/Debian:**
```bash
sudo apt-get install openssl
```

**For macOS (via Homebrew):**
```bash
brew install openssl
```

### Step 2: Generate a Self-Signed Certificate and Private Key
Run the following command to create a self-signed certificate and private key:
```bash
openssl req -newkey rsa:2048 -nodes -keyout keycloak.key -x509 -days 365 -out keycloak.crt
```

This command performs the following:

- `-newkey rsa:2048`: Generates a new 2048-bit RSA key.
- `-nodes`: Disables passphrase encryption on the key.
- `-keyout keycloak.key`: Outputs the private key.
- `-x509`: Outputs a self-signed certificate.
- `-days 365`: Sets the certificate validity for 1 year.
- `-out keycloak.crt`: Outputs the certificate file.

During the process, you’ll be prompted to enter details like country, state, and organization.

After running this command, you’ll have two files:

- `keycloak.key`: Your private key.
- `keycloak.crt`: Your self-signed SSL certificate.

### Step 3: Configure Keycloak to Use the Self-Signed Certificate

#### Create a Java KeyStore (JKS)
Keycloak expects the SSL certificate and key to be stored in a Java KeyStore (JKS) format. Convert your certificate and key to this format as follows:

1. Export your certificate and key to a PKCS12 file:
    ```bash
    openssl pkcs12 -export -in keycloak.crt -inkey keycloak.key -out keycloak.p12 -name keycloak -CAfile keycloak.crt -caname root
    ```

2. Convert the `.p12` file to a Java KeyStore (JKS):
    ```bash
    keytool -importkeystore -deststorepass password -destkeypass password -destkeystore keycloak.jks -srckeystore keycloak.p12 -srcstoretype PKCS12 -alias keycloak
    ```

#### Set Permissions
Ensure proper permissions are set for the certificate and key files:
```bash
chmod 644 /path/to/your/keycloak.crt
chmod 600 /path/to/your/keycloak.key
```

#### Set Ownership
Ensure the files are accessible to the Keycloak user inside the container by setting the ownership:
```bash
sudo chown 1000:1000 /path/to/your/keycloak.key
sudo chown 1000:1000 /path/to/your/keycloak.crt
```

After completing these steps, your Keycloak instance will be configured to use HTTPS with a self-signed SSL certificate.
