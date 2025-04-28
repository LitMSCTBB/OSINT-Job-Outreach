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
  email_sent?: string[];
  twitter_message_sent?: boolean;
}

export async function generatePersonContent(text: string): Promise<Person> {
  console.log(text);
  const res = await axios.post(`${API_BASE}/api/generate-person-content`, { text });
  return res.data;
}

export async function sendPerson(person: Person): Promise<Person> {
  const res = await axios.post(`${API_BASE}/api/send-person`, { person });
  return res.data;
}

interface CompanyPersonRecord {
  name: string;
  profile_link: string;
}

export async function getCompanyPeople(
  url: string,
  domain: string
): Promise<CompanyPersonRecord[]> {
  const res = await axios.post(`${API_BASE}/api/get-company-people`, { url, domain });
  return res.data;
}

export async function getCompletePeopleRecords(): Promise<Person[]> {
  const res = await axios.get(`${API_BASE}/api/get-people-records`);
  return res.data;
}
