import React, { useEffect, useState } from "react";
import { PersonCard } from "./components/PersonCard";
import {
  generatePersonContent,
  sendPerson,
  getCompanyPeople,
  getCompletePeopleRecords,
  Person,
} from "./api";

interface NewPersonCard {
  id: string; // Temporary ID for new cards
  timestamp: number; // For ordering
  initialInfo?: string;
}

function App() {
  const [completePeople, setCompletePeople] = useState<Person[]>([]);
  const [newPersonCards, setNewPersonCards] = useState<NewPersonCard[]>([]);
  const [isAddCompanyOpen, setIsAddCompanyOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reviewingPeople, setReviewingPeople] = useState<Person[]>([]);

  // Add polling effect
  useEffect(() => {
    // Initial fetch
    fetchCompletePeopleRecords();

    // Set up polling interval
    const intervalId = setInterval(fetchCompletePeopleRecords, 60000); // 60000ms = 1 minute

    // Cleanup interval on unmount
    return () => clearInterval(intervalId);
  }, []); // Empty dependency array means this runs once on mount

  // Add fetch function
  const fetchCompletePeopleRecords = async () => {
    try {
      const records = await getCompletePeopleRecords();
      setCompletePeople(records);
      setReviewingPeople((prev) => (prev.filter((p) => !records.includes(p))));
    } catch (err) {
      console.error("Failed to fetch people records:", err);
      setError("Failed to fetch people records");
    }
  };

  const handleAddNewCard = () => {
    setNewPersonCards((prev) => [
      ...prev,
      {
        id: `new-${Date.now()}`,
        timestamp: Date.now(),
      },
    ]);
  };

  const handleRemoveNewCard = (cardId: string) => {
    setNewPersonCards((prev) => prev.filter((card) => card.id !== cardId));
  };

  const handleAddPerson = async (text: string, cardId: string) => {
    try {
      const person = await generatePersonContent(text);
      handleRemoveNewCard(cardId); // Remove this specific card
      console.log("Person added", person);
      setReviewingPeople((prev) => [...prev, person]);
    } catch (err) {
      setError("Failed to add person");
      console.error(err);
    }
  };

  const handleAddCompany = async (url: string, domain: string) => {
    try {
      const res = await getCompanyPeople(url, domain);
      const people = res.map((person) => ({
        id: person.profile_link,
        timestamp: Date.now(),
        initialInfo: `${person.name}\n${person.profile_link}\n${domain}`,
      }));
      // setPeople(people);
      setNewPersonCards(people);
      setIsAddCompanyOpen(false);
    } catch (err) {
      setError("Failed to add company");
      console.error(err);
    }
  };

  const handleSendPerson = async (person: Person, email2: string) => {
    try {
      person.email2 = email2;
      const person2 = await sendPerson(person);
      if (person2.email_sent && person2.twitter_message_sent) {
        setCompletePeople((prev) => [...prev, person2]);
        setReviewingPeople((prev) =>
          prev.filter((p) => { console.log(p.name, person2.name); return p.name !== person2.name; })
        );
      }
      setSuccess(
        `Successfully sent to emails ${person2.email_sent?.join(", ")}${
          person2.twitter_message_sent && " and the twitter message"
        }`
      );
    } catch (err) {
      setError(`Failed to send outreach for ${person.name}`);
      console.error(err);
    }
  };

  const handleRedraft = async (person: Person) => {
    try {
      // remove from completePeople
      setCompletePeople((prev) => prev.filter((p) => p.name !== person.name));
      // add to reviewingPeople
      setReviewingPeople((prev) => [...prev, person]);
    } catch (err) {
      setError(`Failed to redraft for ${person.name}`);
      console.error(err);
    }
  };

  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      const isInputFocused =
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement;

      // For '/' shortcut
      if (event.key === "/" && !isInputFocused) {
        event.preventDefault();
        handleAddNewCard();
      }

      // For 'c' shortcut
      if (
        (event.key === "c" || event.key === "C") &&
        !isInputFocused &&
        !event.ctrlKey &&
        !event.metaKey
      ) {
        event.preventDefault();
        setIsAddCompanyOpen(true);
      }

      if (event.key === "Escape" && isAddCompanyOpen) {
        event.preventDefault();
        setIsAddCompanyOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyPress);
    return () => document.removeEventListener("keydown", handleKeyPress);
  }, [isAddCompanyOpen]);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Top Bar */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Outreach Tool</h1>
        <div className="flex gap-4">
          <div className="relative">
            <button
              onClick={handleAddNewCard}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2 relative"
              aria-label="Add Person (Press '/' to trigger)"
              title="Add Person (Press '/' to trigger)"
            >
              <span>Add Person</span>
              <kbd className="text-sm bg-blue-600 px-1.5 py-0.5 rounded font-mono">
                /
              </kbd>
            </button>
          </div>
          <button
            onClick={() => setIsAddCompanyOpen(true)}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2"
          >
            <span>Add Company People</span>
            <kbd className="text-sm bg-blue-600 px-1.5 py-0.5 rounded font-mono">
              C
            </kbd>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 p-6">
        {/* Add Company Card */}
        {isAddCompanyOpen && (
          <div className="bg-white rounded-lg p-6 shadow-lg border mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Add Company</h2>
              <button
                onClick={() => setIsAddCompanyOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <span className="sr-only">Close</span>×
              </button>
            </div>
            <div className="space-y-4">
              <div className="flex gap-4">
                <div className="flex-1">
                  <label
                    htmlFor="companyUrl"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Company LinkedIn URL
                  </label>
                  <input
                    id="companyUrl"
                    type="text"
                    className="w-full p-3 border rounded font-mono"
                    placeholder="https://linkedin.com/company/example"
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                        const domainInput = document.querySelector(
                          "input[placeholder='example.com']"
                        ) as HTMLInputElement;
                        if (!e.currentTarget.value || !domainInput.value) {
                          setError("Both LinkedIn URL and domain are required");
                          return;
                        }
                        handleAddCompany(
                          e.currentTarget.value,
                          domainInput.value
                        );
                      }
                    }}
                    autoFocus
                  />
                </div>
                <div className="flex-1">
                  <label
                    htmlFor="companyDomain"
                    className="block text-sm font-medium text-gray-700 mb-1"
                  >
                    Company Domain
                  </label>
                  <input
                    id="companyDomain"
                    type="text"
                    className="w-full p-3 border rounded font-mono"
                    placeholder="example.com"
                    onKeyDown={(e) => {
                      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                        const urlInput = document.querySelector(
                          "input[placeholder='https://linkedin.com/company/example']"
                        ) as HTMLInputElement;
                        if (!urlInput.value || !e.currentTarget.value) {
                          setError("Both LinkedIn URL and domain are required");
                          return;
                        }
                        handleAddCompany(urlInput.value, e.currentTarget.value);
                      }
                    }}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    const urlInput = document.querySelector(
                      "input[placeholder='https://linkedin.com/company/example']"
                    ) as HTMLInputElement;
                    const domainInput = document.querySelector(
                      "input[placeholder='example.com']"
                    ) as HTMLInputElement;

                    if (!urlInput.value || !domainInput.value) {
                      setError("Both LinkedIn URL and domain are required");
                      return;
                    }

                    handleAddCompany(urlInput.value, domainInput.value);
                  }}
                  className="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600 whitespace-nowrap flex items-center gap-2"
                >
                  <span>Add Company</span>
                  <kbd className="text-sm bg-green-600 px-1.5 py-0.5 rounded font-mono">
                    ⌘↵
                  </kbd>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Three-Column Layout */}
        <div className="grid grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
          {/* Left Column */}
          <div className="min-h-0">
            <h2 className="text-lg font-medium text-gray-700 sticky top-0 bg-white pb-4">
              Add New People
            </h2>
            <div className="overflow-y-auto h-[calc(100%-2rem)]">
              <div className="space-y-4">
                {newPersonCards.map((card) => (
                  <PersonCard
                    mode="input"
                    key={card.id}
                    onAddNewPerson={(text) => handleAddPerson(text, card.id)}
                    onCancel={() => handleRemoveNewCard(card.id)}
                    initialInfo={card.initialInfo}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Middle Column */}
          <div className="min-h-0">
            <h2 className="text-lg font-medium text-gray-700 sticky top-0 bg-white pb-4">
              Review Drafts
            </h2>
            <div className="overflow-y-auto h-[calc(100%-2rem)]">
              <div className="space-y-4">
                {reviewingPeople
                  .filter((person) => person.email !== null)
                  .map((person) => (
                    <PersonCard
                      mode="reviewing"
                      key={person.name}
                      person={person}
                      onSendPerson={(email2: string) =>
                        handleSendPerson(person, email2)
                      }
                    />
                  ))}
              </div>
            </div>
          </div>

          {/* Right Column */}
          <div className="min-h-0">
            <h2 className="text-lg font-medium text-gray-700 sticky top-0 bg-white pb-4">
              Completed
            </h2>
            <div className="overflow-y-auto h-[calc(100%-2rem)]">
              <div className="space-y-4">
                {completePeople
                  .filter(
                    (person) =>
                      person.email2 !== null && person.email_sent !== null
                  )
                  .map((person) => (
                    <PersonCard
                      key={person.name}
                      person={person}
                      mode="completed"
                      onRedraft={() => handleRedraft(person)}
                    />
                  ))}
                {completePeople.length === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    No completed records yet
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Error and Success Messages */}
      <div className="fixed bottom-4 right-4 space-y-2">
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded shadow-lg">
            <div className="flex justify-between">
              <p className="text-red-700">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-500 text-sm hover:text-red-700"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}
        {success && (
          <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded shadow-lg">
            <p className="text-green-700">{success}</p>
            <button
              onClick={() => setSuccess(null)}
              className="text-green-500 text-sm hover:text-green-700"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
