
count(kube_namespace_status_phase)/2

http://architect-platform-eng.coder:4200/

http://platform-auth.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
http://teams-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
http://teams-api.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
http://argo.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/

TODO:
* crosscheck the keycloak configuration, make sure everything is added
* update the cve/quality constraints to apply to teams-ui/api/operator ...
    * check nginx unprivileged

* check coder IP changes: ping architect-platform-eng.coder
* add demo walkthrough + check PPT
* create slide with components/ports/urls
* PR updates:
    * docker build app 
    * refer to existing services in teams-ui deployment


# Preparation
* Open Grafana and update view to count NS
* Open powershell for TCLI
* Open vscode terminal
* Delete all teams from API service
* port-forward argocd
```
kubectl port-forward svc/argocd-server -n argocd 7080:443
```


# Team creation test
Open UI http://teams-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
Open Grafana with NS count
> Show NS count

Follow operator logs
```
k logs -l app=teams-operator -f
```

Create "Frontend team" in the UI

> Watch operator creating the namespace
Look for created namespace 
```
k get ns |grep team- 
```

> Refresh teams UI and show status

# Team invalid creation test
Open UI http://teams-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/

Follow operator logs
```
k logs -l app=teams-operator -f
```

Create "Invalid::team" in the UI

> Watch operator failing

> Refresh UI and show update

Update namespace using cli
```
tcli list
tcli update -n qa-team -i id
 ```
> Watch operator creating namespace

> Refresh UI and show update

# End-to-end flow

Use case: team wants to onboard and has its first app ready in a github repo (following naming conventions)

* Show github repo: https://github.com/joengineering/team-backend-team/tree/main/argo

* Show application UI http://backend-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
> Expect 404 as not deployed

* Open ArgoCD at the left: https://architect-platform-eng.coder:7080/applications 
* Open teams UI at the right
* Create "Backend team" through UI

> Watch a new application appearing in argocd

> Open application and show deployed resources

> Show application UI http://backend-ui.fd60-627a-a42b-42d3-861a-6987-3179-4d87.sslip.io/
> this should now return a message

* Delete "Backend team" through UI
> Watch the application disappearing from argocd

> show namespace is gone and UI application no longer responding



