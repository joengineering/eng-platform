#!/usr/bin/env python3
"""
Teams CLI - A simple command-line interface for the Teams API
"""

import argparse
import json
import sys
import requests
from typing import Optional

API_BASE_URL = "http://localhost:4200"

class TeamsAPI:
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        
    def _make_request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        """Make HTTP request to the API"""
        url = f"{self.base_url}{endpoint}"
        #print(f"Calling url {url}")
        try:
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
            elif method == "PUT":
                response = requests.put(url, json=data, headers={"Content-Type": "application/json"})
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers={"Content-Type": "application/json"})
            elif method == "DELETE":
                response = requests.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            print(f"❌ Error: Could not connect to API at {self.base_url}")
            print("   Make sure the Teams API is running")
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                error_detail = response.json().get("detail", "Bad request")
                print(f"❌ Error: {error_detail}")
            elif response.status_code == 404:
                print("❌ Error: Team not found")
            else:
                print(f"❌ HTTP Error {response.status_code}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            sys.exit(1)

    def health_check(self):
        """Check API health"""
        result = self._make_request("GET", "/health")
        status = result.get("status", "unknown")
        teams_count = result.get("teams_count", 0)
        print(f"✅ API Status: {status}")
        print(f"📊 Teams Count: {teams_count}")

    def create_team(self, name: str):
        """Create a new team"""
        result = self._make_request("POST", "/teams", {"name": name})
        print(f"✅ Created team: {result['name']}")
        print(f"🆔 Team ID: {result['id']}")
        print(f"📅 Created: {result['created_at']}")
        print(f"📅 Updated: {result['updated_at']}")
        print(f"📅 Status: {result['status']}")

    def update_team(self, id: str, name: str):
        """Create a new team"""
        result = self._make_request("PATCH", "/teams/"+id, {"name": name})
        print(f"✅ Updated team: {result['name']}")
        print(f"🆔 Team ID: {result['id']}")
        print(f"📅 Created: {result['created_at']}")
        print(f"📅 Updated: {result['updated_at']}")
        print(f"📅 Status: {result['status']}")

    def list_teams(self, format: str):
        """List all teams"""
        teams = self._make_request("GET", "/teams")
        if not teams:
            if format == "text": 
                print("📭 No teams found")
            else: 
                print("[]") 
            return
        if format == "text":
            print(f"📋 Found {len(teams)} team(s):")
            print("-" * 60)
            for team in teams:
                print(f"🏷️  Name: {team['name']}")
                print(f"🆔 ID: {team['id']}")
                print(f"📅 Created: {team['created_at']}")
                print(f"📅 Updated: {team['updated_at']}")
                print(f"📅 Status: {team['status']}")
                print("-" * 60)
        elif format== "json": 
            records = []
            for team in teams:
                records.append(f"{{\"id\":\"{team['id']}\",\"name\":\"{team['name']}\",\"createdAt\":\"{team['created_at']}\"}}")
            print("["+",".join(records)+"]")    
        elif format== "json-pretty": 
            print("[")
            records = []
            
            for i, team in enumerate(teams):
                if i>0:
                    print(",{")
                else: 
                    print ("{")
                print(f"    \"id\":\"{team['id']}\",")
                print(f"    \"name\":\"{team['name']}\",")
                print(f"    \"createdAt\":\"{team['created_at']}\"")
                print(f"    \"updatedAt\":\"{team['updated_at']}\"")
                print(f"    \"status\":\"{team['status']}\"")
                print("}") 
            print("]")
        else: 
            print(f"Unknown format: {format}")
            sys.exit(-1)

    def get_team(self, team_id: str):
        """Get a specific team by ID"""
        team = self._make_request("GET", f"/teams/{team_id}")
        print(f"🏷️  Name: {team['name']}")
        print(f"🆔 ID: {team['id']}")
        print(f"📅 Created: {team['created_at']}")
        print(f"📅 Updated: {team['updated_at']}")
        print(f"📅 Status: {team['status']}")

    def delete_team(self, team_id: str):
        """Delete a team"""
        result = self._make_request("DELETE", f"/teams/{team_id}")
        print(f"✅ {result['message']}")

def main():
    parser = argparse.ArgumentParser(
        description="Teams CLI - Manage teams via the Teams API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  teams-cli health                    # Check API health
  teams-cli create "Backend Team"     # Create a new team
  teams-cli list                      # List all teams
  teams-cli get <team-id>            # Get specific team
  teams-cli delete <team-id>         # Delete a team
  teams-cli update -i <team-id> -n <name>            # Update name for team
        """
    )
    
    parser.add_argument(
        "--url", 
        default=API_BASE_URL,
        help=f"API base URL (default: {API_BASE_URL})"
    )
 
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Health command
    subparsers.add_parser("health", help="Check API health")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new team")
    create_parser.add_argument("name", help="Team name")

    # update command
    update_parser = subparsers.add_parser("update", help="Update a team")
    update_parser.add_argument("-i","--id", help="Team id")
    update_parser.add_argument("-n", "--name", help="Team name")

    # List command
    list_parser = subparsers.add_parser("list", help="List all teams")
    list_parser.add_argument(
        "-o", "--output", 
        default="text",
        help=f"output format (default: text)"
    )

    # Get command
    get_parser = subparsers.add_parser("get", help="Get a specific team")
    get_parser.add_argument("team_id", help="Team ID")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a team")
    delete_parser.add_argument("team_id", help="Team ID")

    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize API client
    api = TeamsAPI(args.url)
    
    # Execute command
    try:
        if args.command == "health":
            api.health_check()
        elif args.command == "create":
            api.create_team(args.name)
        elif args.command == "update":
            api.update_team(args.id, args.name)
        elif args.command == "list":
            api.list_teams(args.output)
        elif args.command == "get":
            api.get_team(args.team_id)
        elif args.command == "delete":
            api.delete_team(args.team_id)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main()
