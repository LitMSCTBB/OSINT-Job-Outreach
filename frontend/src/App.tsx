import React, { useEffect, useState } from "react";
import { PersonCard } from "./components/PersonCard";
import {
  generatePersonContent,
  sendPerson,
  getCompanyPeople,
  Person,
} from "./api";

interface NewPersonCard {
  id: string; // Temporary ID for new cards
  timestamp: number; // For ordering
}

function App() {
  const [people, setPeople] = useState<Person[]>([]);
  const [newPersonCards, setNewPersonCards] = useState<NewPersonCard[]>([]);
  const [isAddCompanyOpen, setIsAddCompanyOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter people based on status
  const incompletePeople = people.filter(
    (person) => person.email == null || person.email2 == null
  );

  const draftReadyPeople = people.filter((person) => person.email !== null);

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
      setIsLoading(true);
      await generatePersonContent(text);
      handleRemoveNewCard(cardId); // Remove this specific card
    } catch (err) {
      setError("Failed to add person");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddCompany = async (url: string) => {
    try {
      setIsLoading(true);
      const res = await getCompanyPeople(url);
      const people = res.map((person) => ({
        id: person.profile_link,
        name: person.name,
        profile_link: person.profile_link,
        domain: person.profile_link.split("/")[4],
      }));
      setPeople(people);
      setIsAddCompanyOpen(false);
    } catch (err) {
      setError("Failed to add company");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendPerson = async (person: Person) => {
    try {
      setIsLoading(true);
      const res = await sendPerson(person);
      console.log(res);
    } catch (err) {
      setError(`Failed to send outreach for ${person.name}`);
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Top Bar */}
      <div className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Outreach Tool</h1>
        <div className="flex gap-4">
          <button
            onClick={handleAddNewCard}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2"
          >
            <span>Add Person</span>
            <span className="text-sm opacity-75">/</span>
          </button>
          <button
            onClick={() => setIsAddCompanyOpen(true)}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2"
          >
            <span>Add Company</span>
            <span className="text-sm opacity-75">⌘K</span>
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border-l-4 border-red-500 p-4 m-4">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-500 text-sm hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading Indicator */}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-4 rounded-lg">Processing...</div>
        </div>
      )}

      {/* Two-Column Layout */}
      <div className="flex-1 grid grid-cols-2 gap-6 p-6 bg-gray-50 overflow-auto">
        {/* Left Column - Incomplete Entries */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-700">
            Incomplete Entries
          </h2>
          <div className="space-y-4">
            {/* New Person Cards */}
            {newPersonCards.map((card) => (
              <PersonCard
                key={card.id}
                onSubmit={(text) => handleAddPerson(text, card.id)}
                onCancel={() => handleRemoveNewCard(card.id)}
              />
            ))}
            {/* Existing Incomplete People */}
            {incompletePeople.map((person) => (
              <PersonCard
                key={person.name}
                person={person}
                onSubmit={(text) => handleAddPerson(text, person.name)}
              />
            ))}
          </div>
        </div>

        {/* Right Column - Review Drafts */}
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-700">Review Drafts</h2>
          <div className="space-y-4">
            {draftReadyPeople.map((person) => (
              <PersonCard
                key={person.name}
                person={person}
                onSubmit={(text) => handleAddPerson(text, person.name)}
                onSend={() => handleSendPerson(person)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Add Company Dialog */}
      {isAddCompanyOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg">
            <div className="space-y-4">
              <h2 className="text-xl font-semibold">Add Company</h2>
              <input
                type="text"
                className="w-full p-3 border rounded font-mono"
                placeholder="Company LinkedIn URL"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleAddCompany(e.currentTarget.value);
                  }
                }}
              />
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setIsAddCompanyOpen(false)}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    const input = document.querySelector(
                      "input"
                    ) as HTMLInputElement;
                    handleAddCompany(input.value);
                  }}
                  className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                >
                  Add Company
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
