import React, { useState, useRef, useEffect } from "react";
import { Person } from "../api";
import { CopyableTextArea } from "./CopyableTextArea";

type Mode = "input" | "reviewing" | "completed";

interface Props {
  mode: Mode;
  person?: Person;
  onAddNewPerson?: (text: string) => Promise<void>;
  onSendPerson?: (email2: string) => Promise<void>;
  onCancel?: () => void;
  onRedraft?: () => Promise<void>;
  initialInfo?: string;
}

/**
 * Formats a Twitter/X handle or URL into either a full URL or @handle format
 * @param input Twitter/X handle, URL, or any string containing a handle
 * @param format 'link' for full URL or '@handle' for handle format
 * @returns Formatted handle or link
 *
 * Examples:
 * formatTwitter('johndoe', 'link') => 'https://twitter.com/johndoe'
 * formatTwitter('https://x.com/johndoe', '@handle') => '@johndoe'
 */
export function formatTwitter(
  input: string | undefined | null,
  format: "link" | "@handle"
): string {
  if (!input) return "";

  // Extract handle from various formats
  let handle = input
    .trim()
    .toLowerCase()
    .replace(/^@/, "") // Remove @ if present
    .replace(/^https?:\/\/(www\.)?(twitter\.com|x\.com)\//, "") // Remove Twitter or X URL
    .replace(/^(twitter\.com|x\.com)\//, "") // Remove shorter URL format
    .replace(/\/$/, "") // Remove trailing slash if present
    .replace(/[?#].*$/, ""); // Remove query params and hash

  // Return requested format
  if (format === "link") {
    return `https://twitter.com/${handle}`; // Still using twitter.com for consistency
  } else {
    return `@${handle}`;
  }
}

const StatusIndicator = ({ mode }: { mode: Mode }) => (
  <div className="flex items-center gap-2 mt-2">
    <div
      className={`w-2 h-2 rounded-full ${
        mode === "completed"
          ? "bg-green-400"
          : mode === "reviewing"
          ? "bg-blue-400 animate-pulse"
          : "bg-gray-400"
      }`}
    />
    <span className="text-sm text-gray-600 capitalize">
      {mode === "completed" ? "completed" : "processing"}
    </span>
  </div>
);

const handleKeyDown = (
  e: React.KeyboardEvent<HTMLTextAreaElement>,
  submitAction: () => Promise<void>
) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    console.log("ctrl + Enter key pressed");
    e.preventDefault();
    submitAction();
  }
};

export const PersonCard: React.FC<Props> = ({
  mode,
  person,
  onAddNewPerson,
  onSendPerson,
  onCancel,
  onRedraft,
  initialInfo,
}) => {
  const [inputText, setInputText] = useState(
    person?.email2 || person?.email || (mode === "input" && initialInfo) || ""
  );
  const [editedEmail, setEditedEmail] = useState(person?.email || "");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isInsightsOpen, setIsInsightsOpen] = useState(false);
  const [possibleEmails, setPossibleEmails] = useState(
    person?.possible_emails?.join("\n") || ""
  );

  useEffect(() => {
    if (!person && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, []);

  // Input mode (new person)
  if (mode === "input") {
    return (
      <div className="border rounded-lg p-4 shadow-md bg-white">
        <h2 className="text-xl font-semibold mb-3">Add New Person</h2>
        <CopyableTextArea
          ref={textareaRef}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) =>
            handleKeyDown(e, async () => {
              if (inputText.trim()) {
                if (onAddNewPerson) await onAddNewPerson(inputText);
              }
            })
          }
          className="w-full h-40 p-3 border rounded font-mono text-sm bg-gray-50 overflow-auto whitespace-pre-wrap focus:bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          placeholder={`Paste person info here. Example:

Jesse Zhang
https://linkedin.com/in/jesse
@jesseontwitter
Works at decagon.ai
Met at hackathon, interested in LLMs`}
          spellCheck={false}
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
              if (onAddNewPerson) await onAddNewPerson(inputText);
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

  if (mode === "reviewing" && person) {
    return (
      <div className="border rounded-lg p-4 shadow-md bg-white space-y-4">
        {/* Top Section - Person Info */}
        <div>
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-xl font-semibold">
                {person?.profile_link && (
                  <a
                    href={person.profile_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 block hover:underline"
                  >
                    {person.name}
                  </a>
                )}
              </h2>
              <p className="text-sm text-gray-500">{person.domain}</p>
            </div>
          </div>
          <div className="space-y-2 mt-2">
            {person.twitter_handle && (
              <a
                href={`${formatTwitter(person.twitter_handle, "link")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 block hover:underline"
              >
                {formatTwitter(person.twitter_handle, "@handle")}
              </a>
            )}
          </div>

          <StatusIndicator mode={mode} />

          {/* Show insights if available */}
          {person.insights && (
            <div className="mt-4">
              <button
                onClick={() => setIsInsightsOpen(!isInsightsOpen)}
                className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <h3 className="font-medium text-sm">Insights</h3>
                <svg
                  className={`w-4 h-4 transform transition-transform ${
                    isInsightsOpen ? "rotate-180" : ""
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              <div
                className={`transition-all duration-200 ${
                  isInsightsOpen
                    ? "opacity-100 mt-2"
                    : "opacity-0 max-h-0 overflow-hidden"
                }`}
              >
                <p className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600 whitespace-pre-wrap">
                  {person.insights}
                </p>
              </div>
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

        {/* Bottom Section - Email */}
        {person.email && (
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-medium">Edit Message</h3>
            </div>

            <CopyableTextArea
              value={editedEmail}
              onChange={(e) => setEditedEmail(e.target.value)}
              onKeyDown={(e) =>
                handleKeyDown(e, async () => {
                  if (onSendPerson) {
                    await onSendPerson(editedEmail);
                  }
                })
              }
              className="w-full p-3 border rounded font-mono text-sm bg-gray-50 overflow-auto whitespace-pre-wrap focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y min-h-[300px]"
              rows={10}
              spellCheck={false}
            />

            {/* Possible emails */}
            {
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">
                  Email Addresses to Send To
                </h4>
                <CopyableTextArea
                  value={possibleEmails}
                  onChange={(e) => {
                    setPossibleEmails(e.target.value);
                    // Update the person object with new emails
                    if (person) {
                      person.possible_emails = e.target.value
                        .split("\n")
                        .map((email) => email.trim())
                        .filter((email) => email !== "");
                    }
                  }}
                  className="w-full p-3 border rounded font-mono text-sm bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                  placeholder="Enter email addresses (one per line)"
                  rows={5}
                  spellCheck={false}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Enter one email address per line
                </p>
              </div>
            }

            <div className="mt-4 flex justify-end">
              {onSendPerson && (
                <button
                  onClick={() => onSendPerson(editedEmail)}
                  className="px-6 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
                >
                  Send Email
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    );
  }

  if (mode === "completed" && person) {
    // show the list of email addresses sent to, if twitter handle was sent to, linkedin link, twitter link, the email, and then a collapsibl that shows the json when expanded
    return (
      <div className="border rounded-lg p-4 shadow-md bg-white space-y-4">
        {/* Top Section - Person Info */}
        <div>
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-xl font-semibold">
                {person?.profile_link && (
                  <a
                    href={person.profile_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 block hover:underline"
                  >
                    {person.name}
                  </a>
                )}
              </h2>
              <p className="text-sm text-gray-500">{person.domain}</p>
            </div>
            {mode === "completed" && onRedraft && (
              <button
                onClick={onRedraft}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                title="If the information was scraped incorrectly, click to move this card to the review section where you can edit the email and send it manually."
              >
                Redraft
              </button>
            )}
          </div>
          <div className="space-y-2 mt-2">
            {person.twitter_handle && (
              <a
                href={`${formatTwitter(person.twitter_handle, "link")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-400 block hover:underline"
              >
                {formatTwitter(person.twitter_handle, "@handle")}
              </a>
            )}
          </div>

          <StatusIndicator mode={mode} />

          {/* Show insights if available */}
          {person.insights && (
            <div className="mt-4">
              <button
                onClick={() => setIsInsightsOpen(!isInsightsOpen)}
                className="w-full flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <h3 className="font-medium text-sm">Insights</h3>
                <svg
                  className={`w-4 h-4 transform transition-transform ${
                    isInsightsOpen ? "rotate-180" : ""
                  }`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </button>
              <div
                className={`transition-all duration-200 ${
                  isInsightsOpen
                    ? "opacity-100 mt-2"
                    : "opacity-0 max-h-0 overflow-hidden"
                }`}
              >
                <p className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600 whitespace-pre-wrap">
                  {person.insights}
                </p>
              </div>
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

        {/* Bottom Section - Email */}
        {person.email && (
          <div className="border-t pt-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-medium">Final Email</h3>
            </div>

            <CopyableTextArea
              value={person.email2 || person.email || ""}
              readOnly
              className="w-full p-3 border rounded font-mono text-sm bg-gray-50 whitespace-pre-wrap"
              spellCheck={false}
            />

            {/* Sent email */}
            {person.email_sent && (
              <div className="mt-4">
                <h4 className="text-sm font-medium mb-2">Sent to Emails</h4>
                <CopyableTextArea
                  value={person.email_sent.join("\n")}
                  readOnly
                  className="w-full p-3 border rounded font-mono text-sm bg-gray-50 overflow-auto whitespace-pre-wrap resize-y"
                  spellCheck={false}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
};
