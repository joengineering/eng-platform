// src/app/models/team.model.ts
export interface Team {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  status: string;
}

export interface TeamCreate {
  name: string;
}
