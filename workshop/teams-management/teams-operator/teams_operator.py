#!/usr/bin/env python3
"""
Teams Operator - Creates Kubernetes namespaces when teams are created in the Teams API
"""

import asyncio
import json
import logging
import os
import time
from typing import Set, Dict, Any
import aiohttp
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('teams-operator')

class TeamsOperator:
    def __init__(self):
        self.teams_api_url = os.getenv('TEAMS_API_URL', 'http://teams-api-service:80')
        self.poll_interval = int(os.getenv('POLL_INTERVAL', '30'))  # seconds
        self.known_teams: Set[str] = set()
        self.team_namespaces: Dict[str, str] = {}
        
        # Initialize Kubernetes client
        try:
            # Try in-cluster config first (when running in pod)
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            # Fall back to local kubeconfig (for development)
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")
        
        self.k8s_core_v1 = client.CoreV1Api()
        
    def sanitize_namespace_name(self, team_name: str) -> str:
        """Convert team name to valid Kubernetes namespace name"""
        # Lowercase, replace spaces/special chars with hyphens, remove consecutive hyphens
        namespace = team_name.lower()
        namespace = ''.join(c if c.isalnum() else '-' for c in namespace)
        namespace = '-'.join(filter(None, namespace.split('-')))  # Remove consecutive hyphens
        
        # Ensure it starts and ends with alphanumeric
        namespace = namespace.strip('-')
        
        # Kubernetes namespace names must be <= 63 characters
        if len(namespace) > 63:
            namespace = namespace[:63].rstrip('-')
            
        # Add prefix to avoid conflicts
        namespace = f"team-{namespace}"
        
        return namespace
    
    async def fetch_teams(self) -> list:
        """Fetch current teams from the Teams API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.teams_api_url}/teams") as response:
                    if response.status == 200:
                        teams = await response.json()
                        logger.debug(f"Fetched {len(teams)} teams from API")
                        return teams
                    else:
                        logger.error(f"Failed to fetch teams: HTTP {response.status}")
                        return []
        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to Teams API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching teams: {e}")
            return []
    

    async def update_status(self, team_id: str, status: str) -> dict | None:
        """
        Patch a team status on the Teams API.
        """

        update_payload = { "status": status}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    f"{self.teams_api_url}/teams/{team_id}",
                    json=update_payload
                ) as response:

                    if response.status == 200:
                        updated_team = await response.json()
                        logger.debug(f"Updated team {team_id} successfully")
                        return updated_team

                    elif response.status == 404:
                        logger.error(f"Team {team_id} not found (404)")
                        return None

                    else:
                        logger.error(
                            f"Failed to update team {team_id}: HTTP {response.status}"
                        )
                        return None

        except aiohttp.ClientError as e:
            logger.error(f"Error connecting to Teams API: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error updating team {team_id}: {e}")
            return None
    
    def create_namespace(self, team_id: str, team_name: str, namespace_name: str) -> bool:
        """Create a Kubernetes namespace for the team"""
        try:
            # Define namespace metadata
            namespace_body = client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=namespace_name,
                    labels={
                        "app.kubernetes.io/managed-by": "teams-operator",
                        "teams.example.com/team-id": team_id,
                        "teams.example.com/team-name": team_name.replace(" ", "-").lower()
                    },
                    annotations={
                        "teams.example.com/original-team-name": team_name,
                        "teams.example.com/created-by": "teams-operator",
                        "teams.example.com/team-id": team_id
                    }
                )
            )
            
            # Create the namespace
            self.k8s_core_v1.create_namespace(body=namespace_body)
            logger.info(f"✅ Created namespace '{namespace_name}' for team '{team_name}' (ID: {team_id})")
            return True
            
        except ApiException as e:
            if e.status == 409:  # Namespace already exists
                logger.warning(f"⚠️ Namespace '{namespace_name}' already exists")
                return True
            else:
                logger.error(f"❌ Failed to create namespace '{namespace_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error creating namespace: {e}")
            return False

    def delete_argocd_application(self, app_name: str) -> bool:
        api = client.CustomObjectsApi()

        try:
            api.delete_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace="argocd",
                plural="applications",
                name=app_name
            )
            logger.info(f"🗑️ Deleted Argo CD Application '{app_name}'")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"⚠️ Application '{app_name}' not found (already deleted?)")
                return True
            logger.error(f"❌ Failed to delete Application '{app_name}': {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error deleting Application '{app_name}': {e}")
            return False


    def delete_argocd_project(self, project_name: str) -> bool:
        api = client.CustomObjectsApi()

        try:
            api.delete_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace="argocd",
                plural="appprojects",
                name=project_name
            )
            logger.info(f"🗑️ Deleted Argo CD AppProject '{project_name}'")
            return True

        except ApiException as e:
            if e.status == 404:
                logger.warning(f"⚠️ AppProject '{project_name}' not found (already deleted?)")
                return True
            logger.error(f"❌ Failed to delete AppProject '{project_name}': {e}")
            return False

        except Exception as e:
            logger.error(f"❌ Unexpected error deleting AppProject '{project_name}': {e}")
            return False


    def delete_namespace(self, namespace_name: str, team_name: str) -> bool:
        """Delete a Kubernetes namespace when team is removed"""
        try:
            self.k8s_core_v1.delete_namespace(name=namespace_name)
            logger.info(f"🗑️ Deleted namespace '{namespace_name}' for removed team '{team_name}'")
            return True
        except ApiException as e:
            if e.status == 404:  # Namespace doesn't exist
                logger.warning(f"⚠️ Namespace '{namespace_name}' not found (already deleted?)")
                return True
            else:
                logger.error(f"❌ Failed to delete namespace '{namespace_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting namespace: {e}")
            return False

    def create_or_update_argocd_application(self, app_name: str, project_name: str, namespace_name: str, repo_url: str, path: str) -> bool:
        api = client.CustomObjectsApi()

        app_body = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {
                "name": app_name,
                "namespace": "argocd",
                "labels": {
                    "teams.eng.platform/project": project_name
                }
            },
            "spec": {
                "project": project_name,
                "source": {
                    "repoURL": repo_url,
                    "path": path,
                    "targetRevision": "HEAD"
                },
                "destination": {
                    "namespace": namespace_name,
                    "server": "https://kubernetes.default.svc"
                },
                "syncPolicy": {
                    "automated": {
                        "enabled": True,
                        "prune": True,
                        "selfHeal": True
                    }
                }
            }
        }

        try:
            api.create_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace="argocd",
                plural="applications",
                body=app_body
            )
            logger.info(f"✅ Created Argo CD Application '{app_name}'")
            return True

        except ApiException as e:
            if e.status == 409:
                # Already exists → update it
                try:
                    api.patch_namespaced_custom_object(
                        group="argoproj.io",
                        version="v1alpha1",
                        namespace="argocd",
                        plural="applications",
                        name=app_name,
                        body=app_body
                    )
                    logger.info(f"🔄 Updated existing Argo CD Application '{app_name}'")
                    return True
                except Exception as e2:
                    logger.error(f"❌ Failed to update Application '{app_name}': {e2}")
                    return False
            else:
                logger.error(f"❌ Failed to create Application '{app_name}': {e}")
                return False


    def create_or_update_argocd_project(self, project_name: str, team_id: str, team_name: str, namespace_name: str) -> bool:
        api = client.CustomObjectsApi()

        project_body = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "AppProject",
            "metadata": {
                "name": project_name,
                "namespace": "argocd",
                "labels": {
                    "teams.eng.platform/team-id": team_id,
                    "teams.eng.platform/team-name": team_name.replace(" ", "-").lower(),
                },
                "annotations": {
                    "teams.eng.platform/original-team-name": team_name,
                    "teams.eng.platform/created-by": "teams-operator",
                },
                "finalizers": ["resources-finalizer.argocd.argoproj.io"]
            },
            "spec": {
                "description": f"Project for team {team_name}",
                "sourceRepos": ["*"],
                "destinations": [
                    {
                        "namespace": namespace_name,
                        "server": "https://kubernetes.default.svc",
                        "name": "in-cluster"
                    }
                ],
                "clusterResourceWhitelist": [
                ],
                "namespaceResourceBlacklist": [
                    {"group": "", "kind": "ResourceQuota"},
                    {"group": "", "kind": "LimitRange"},
                    {"group": "", "kind": "NetworkPolicy"},
                ],
                "orphanedResources": {"warn": False},
            }
        }

        try:
            api.create_namespaced_custom_object(
                group="argoproj.io",
                version="v1alpha1",
                namespace="argocd",
                plural="appprojects",
                body=project_body
            )
            logger.info(f"✅ Created Argo CD AppProject '{project_name}'")
            return True

        except ApiException as e:
            if e.status == 409:
                # Already exists → update it
                try:
                    api.patch_namespaced_custom_object(
                        group="argoproj.io",
                        version="v1alpha1",
                        namespace="argocd",
                        plural="appprojects",
                        name=project_name,
                        body=project_body
                    )
                    logger.info(f"🔄 Updated existing Argo CD AppProject '{project_name}'")
                    return True
                except Exception as e2:
                    logger.error(f"❌ Failed to update AppProject '{project_name}': {e2}")
                    return False
            else:
                logger.error(f"❌ Failed to create AppProject '{project_name}': {e}")
                return False
    

    async def reconcile_teams(self):
        """Main reconciliation loop - sync teams with namespaces"""
        teams = await self.fetch_teams()
        current_teams = {team['id']: team for team in teams}
        current_team_ids = set(current_teams.keys())
        
        # Only teams with successful namespaces should be considered "known"
        known_successful = set(self.team_namespaces.keys())

        # Handle new teams (create namespaces)
        new_or_pending = current_team_ids - known_successful
        for team_id in new_or_pending:
            team = current_teams[team_id]
            team_name = team['name']
            namespace_name = self.sanitize_namespace_name(team_name)
            
            if self.create_namespace(team_id, team_name, namespace_name):
                self.team_namespaces[team_id] = namespace_name
                await self.update_status(team_id, "Created")
                self.create_or_update_argocd_project( namespace_name, team_id, team_name, namespace_name)
                self.create_or_update_argocd_application(namespace_name+"-default", namespace_name, namespace_name, "https://github.com/joengineering/"+namespace_name.replace(" ", "").lower(), "argo")
            else:
                await self.update_status(team_id, "Failed")

        # Handle deleted teams (remove namespaces)
        deleted_teams = known_successful - current_team_ids
        for team_id in deleted_teams:
            if team_id in self.team_namespaces:
                namespace_name = self.team_namespaces[team_id]
                # Get team name from namespace annotations if possible
                team_name = f"team-{team_id}"  # fallback
                
                self.delete_argocd_application(namespace_name+"-default") 
                self.delete_argocd_project(namespace_name)

                if self.delete_namespace(namespace_name, team_name):
                    del self.team_namespaces[team_id]
        
        # Update known teams
        self.known_teams = set(self.team_namespaces.keys())
        
        if new_or_pending or deleted_teams:
            logger.info(f"📊 Reconciliation complete: {len(current_teams)} teams, {len(self.team_namespaces)} namespaces")
    
    async def run(self):
        """Main operator loop"""
        logger.info(f"🚀 Teams Operator starting...")
        logger.info(f"📡 Teams API URL: {self.teams_api_url}")
        logger.info(f"⏰ Poll interval: {self.poll_interval} seconds")
        
        # Initial reconciliation
        await self.reconcile_teams()
        
        # Main loop
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await self.reconcile_teams()
            except KeyboardInterrupt:
                logger.info("👋 Received shutdown signal, exiting...")
                break
            except Exception as e:
                logger.error(f"❌ Error in main loop: {e}")
                await asyncio.sleep(self.poll_interval)

async def main():
    """Entry point"""
    operator = TeamsOperator()
    await operator.run()

if __name__ == "__main__":
    asyncio.run(main())
