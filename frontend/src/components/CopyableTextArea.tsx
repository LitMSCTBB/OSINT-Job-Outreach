import React, { useEffect, useRef, useState, forwardRef } from "react";

interface CopyableTextAreaProps {
  value: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onKeyDown?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  readOnly?: boolean;
  className?: string;
  rows?: number;
  placeholder?: string;
  spellCheck?: boolean;
}

export const CopyableTextArea = forwardRef<
  HTMLTextAreaElement,
  CopyableTextAreaProps
>(
  (
    {
      value,
      onChange,
      onKeyDown,
      readOnly,
      className,
      rows,
      placeholder,
      spellCheck,
    },
    forwardedRef
  ) => {
    const [copied, setCopied] = useState(false);
    const localRef = useRef<HTMLTextAreaElement>(null);
    const ref = (forwardedRef ||
      localRef) as React.RefObject<HTMLTextAreaElement>;

    useEffect(() => {
      if (ref.current) {
        ref.current.style.height = "auto";
        ref.current.style.height = `${ref.current.scrollHeight}px`;
      }
    }, [value]);

    const handleCopy = () => {
      navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    };

    return (
      <div className="relative">
        <textarea
          ref={ref}
          className={className}
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          readOnly={readOnly}
          rows={rows}
          placeholder={placeholder}
          spellCheck={spellCheck}
        />
        <button
          onClick={handleCopy}
          className="absolute top-2 right-2 p-2 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
          title="Copy to clipboard"
        >
          {copied ? (
            <svg
              className="w-4 h-4 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          ) : (
            <svg
              className="w-4 h-4 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"
              />
            </svg>
          )}
        </button>
      </div>
    );
  }
);

CopyableTextArea.displayName = "CopyableTextArea";
