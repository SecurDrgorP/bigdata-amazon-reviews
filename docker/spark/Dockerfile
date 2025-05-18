FROM bitnami/spark:3.4.1

USER root

# Installer quelques dépendances nécessaires
RUN apt-get update && apt-get install -y python3 python3-pip

# Installer findspark pour connecter Spark à Python
RUN pip3 install findspark
