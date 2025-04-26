import React, { useState } from "react";
import { Person } from "../api";


interface Props {
  person?: Person;
  onSubmit: (text: string) => Promise<void>;
  onSend?: () => Promise<void>;
  onCancel?: () => void;
}

export const PersonCard: React.FC<Props> = ({
  person,
  onSubmit,
  onSend,
  onCancel,
}) => {
  const [inputText, setInputText] = useState("");
  const [editedEmail, setEditedEmail] = useState(person?.email || "");
  const [isEditing, setIsEditing] = useState(false);

  // Input mode (new person)
  if (!person) {
    return (
      <div className="border rounded-lg p-4 shadow-md bg-white">
        <h2 className="text-xl font-semibold mb-3">Add New Person</h2>
        <textarea
          className="w-full h-40 p-3 border rounded font-mono text-sm bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={`Paste person info here. Example:

Jesse Zhang
https://linkedin.com/in/jesse
@jesseontwitter
Works at decagon.ai
Met at hackathon, interested in LLMs`}
        />
        <div className="flex justify-end gap-3 mt-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
          )}
          <button
            onClick={async () => {
              await onSubmit(inputText);
              setInputText("");
            }}
            disabled={!inputText.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Add Person
          </button>
        </div>
      </div>
    );
  }

  // Status indicator component
  const StatusIndicator = () => (
    <div className="flex items-center gap-2 mt-2">
      <div
        className={`w-2 h-2 rounded-full ${
          person.email
            ? "bg-green-400"
            : person.email2
            ? "bg-blue-400 animate-pulse"
            : "bg-gray-400"
        }`}
      />
      <span className="text-sm text-gray-600 capitalize">
        {person.email ? "completed" : "processing"}
      </span>
    </div>
  );

  return (
    <div className="border rounded-lg p-4 shadow-md bg-white">
      <div className="grid grid-cols-2 gap-4">
        {/* Person Info Column */}
        <div>
          <h2 className="text-xl font-semibold">{person.name}</h2>
          <p className="text-sm text-gray-500">{person.domain}</p>
          <div className="space-y-2 mt-2">
            {person.profile_link && (
              <a
                href={person.profile_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 block hover:underline"
              >
                LinkedIn Profile
              </a>
            )}
            {person.twitter_handle && (
              <a
                href={`https://twitter.com/${person.twitter_handle}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 block hover:underline"
              >
                @{person.twitter_handle}
              </a>
            )}
          </div>

          <StatusIndicator />

          {/* Show insights if available */}
          {person.insights && (
            <div className="mt-4 p-3 bg-gray-50 rounded text-sm">
              <h3 className="font-medium mb-2">Insights</h3>
              <p className="whitespace-pre-wrap text-gray-600">
                {person.insights}
              </p>
            </div>
          )}

          {/* Show notes if available */}
          {person.notes && (
            <div className="mt-4">
              <h3 className="text-sm font-medium">Notes</h3>
              <p className="text-sm text-gray-600 mt-1">{person.notes}</p>
            </div>
          )}
        </div>

        {/* Email Draft Column */}
        <div>
          {person.email && (
            <>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-lg font-medium">Email Draft</h3>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="text-sm text-blue-500 hover:text-blue-600"
                >
                  {isEditing ? "Preview" : "Edit"}
                </button>
              </div>

              {isEditing ? (
                <textarea
                  className="w-full h-64 p-3 border rounded font-mono text-sm bg-gray-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  value={editedEmail}
                  onChange={(e) => setEditedEmail(e.target.value)}
                />
              ) : (
                <div className="w-full h-64 p-3 border rounded font-mono text-sm bg-gray-50 overflow-auto whitespace-pre-wrap">
                  {editedEmail}
                </div>
              )}

              {/* Possible emails */}
              {person.possible_emails && person.possible_emails.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium mb-2">
                    Possible Email Addresses
                  </h4>
                  <div className="space-y-1">
                    {person.possible_emails.map((email, idx) => (
                      <div
                        key={idx}
                        className="text-sm font-mono text-gray-600"
                      >
                        {email}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Send button */}
              {onSend && (
                <button
                  onClick={onSend}
                  className="mt-4 w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                >
                  Send Outreach
                </button>
              )}
            </>
          )}

          {person.email && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                <svg
                  className="w-12 h-12 mx-auto text-green-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <p className="mt-2">Outreach Completed</p>
              </div>
            </div>
          )}

          {person.email && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-500">
                {person.email ? (
                  <p>Waiting to process...</p>
                ) : (
                  <div className="animate-pulse">
                    <p>Processing...</p>
                    <p className="text-sm mt-2">Gathering information</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
