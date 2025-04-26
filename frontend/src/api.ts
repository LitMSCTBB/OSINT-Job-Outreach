import axios from "axios";

// const API_BASE = import.meta.env.VITE_API_URL;
const API_BASE = "http://localhost:8000";

export interface Person {
  name: string;
  profile_link: string;
  domain: string;
  linkedin_summary?: string;
  twitter_summary?: string;
  insights?: string;
  possible_emails?: string[];
  twitter_handle?: string;
  notes?: string;
  email?: string;
  email2?: string;
}

export async function generatePersonContent(text: string): Promise<Person> {
  const res = await axios.post(`${API_BASE}/generate-person-content`, { text });
  return res.data;
}

export async function sendPerson(person: Person): Promise<string> {
  const res = await axios.post(`${API_BASE}/send_person`, { person });
  return res.data;
}

interface CompanyPersonRecord {
  name: string;
  profile_link: string;
}

export async function getCompanyPeople(
  url: string
): Promise<CompanyPersonRecord[]> {
  const res = await axios.post(`${API_BASE}/get-company-people`, { url });
  return res.data;
}
