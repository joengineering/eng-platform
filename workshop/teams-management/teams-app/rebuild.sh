docker build -t teams-ui:local .
kind load docker-image teams-ui:local --name 5min-idp
kubectl rollout restart deployment teams-ui -n teams-ui