# Servo Control over MQTT

Originally based from [https://github.com/resin-io-projects/simple-server-python](https://github.com/resin-io-projects/simple-server-python)

# AWS setup

Create a keys and certificate and attach a policy to it: 

    wget -O ca_crt.pem https://www.symantec.com/content/en/us/enterprise/verisign/roots/VeriSign-Class%203-Public-Primary-Certification-Authority-G5.pem

    aws iot create-keys-and-certificate --set-as-active \
      --certificate-pem-outfile cl_crt.pem \
      --public-key-outfile public_key.pem \
      --private-key-outfile private_key.pem    
    aws iot attach-principal-policy --principal "<certificate-arn>" --policy-name "PubSubToAnyTopic"
    
Convert certificates and private key to oneline format for inclusion into env variables:
 
     awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' ca_crt.pem
     awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' cl_crt.pem
     awk 'NF {sub(/\r/, ""); printf "%s\\n",$0;}' private_key.pem

# Running
     
When running the app make sure that the following ENV variables are set with the appropriate values:

| Env var        | Value                                   |
|----------------|-----------------------------------------|
|MQTT_HOSTNAME   |MQTT endpoint hostname                   |
|MQTT_PORT       |MQTT endpoint port                       |
|MQTT_CA_CRT     |contents of `ca_crt.pem` in one line     |
|MQTT_CL_CRT     |contents of `cl_crt.pem` in one line     |
|MQTT_PRIVATE_KEY|contents of `private_key.pem` in one line|
