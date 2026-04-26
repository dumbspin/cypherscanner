"use client";

/**
 * ScreenshotPreview — displays a screenshot of the scanned URL via ScreenshotOne API.
 *
 * Features:
 * - Skeleton loader while the image is loading
 * - Dark placeholder card with "Preview unavailable" text on error or missing key
 * - Uses <img> to let the frontend load the screenshot directly from ScreenshotOne
 */

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Dark placeholder shown when no screenshot_url is provided (API key missing)
 * or when the image fails to load from ScreenshotOne.
 *
 * @param {object} props
 * @param {string} props.caption - Optional URL caption shown below placeholder
 * @param {'missing-key' | 'load-error'} [props.errorType] - The type of error that occurred
 */
function UnavailablePlaceholder({ caption, errorType = "missing-key" }) {
  const isLoadError = errorType === "load-error";

  return (
    <div className="card">
      <h3 className="text-text-primary font-semibold mb-4 flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        Page Screenshot
      </h3>

      {/* Dark placeholder card body */}
      <div className="w-full aspect-video rounded-xl bg-background border border-border/50 flex flex-col items-center justify-center gap-3">
        {/* Monitor icon */}
        <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center text-text-muted">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2" strokeDasharray="4 2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
        </div>
        <p className="text-text-muted text-sm font-medium">
          {isLoadError ? "Failed to load preview" : "Preview unavailable"}
        </p>
        <p className="text-text-muted/60 text-xs text-center max-w-xs px-4">
          {isLoadError ? (
            <>
              Check your <span className="font-mono text-accent/70">SCREENSHOTONE_API_KEY</span> validity or monthly quota.
            </>
          ) : (
            <>
              Add a <span className="font-mono text-accent/70">SCREENSHOTONE_API_KEY</span> to enable live page previews.
            </>
          )}
        </p>
      </div>

      {caption && (
        <p className="mt-2 text-text-muted text-xs truncate">Preview: {caption}</p>
      )}
    </div>
  );
}

export default function ScreenshotPreview({ screenshotUrl, targetUrl }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  // No API key configured — show dark placeholder immediately.
  if (!screenshotUrl) {
    return <UnavailablePlaceholder caption={targetUrl} errorType="missing-key" />;
  }

  // Image failed to load — show dark placeholder with specific error.
  if (error) {
    return <UnavailablePlaceholder caption={targetUrl} errorType="load-error" />;
  }

  return (
    <div className="card">
      <h3 className="text-text-primary font-semibold mb-4 flex items-center gap-2">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <line x1="8" y1="21" x2="16" y2="21"/>
          <line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
        Page Screenshot
      </h3>

      <div className="relative w-full aspect-video rounded-xl overflow-hidden border border-border/60 bg-background">
        {/* Skeleton loader: visible until the image resolves */}
        <AnimatePresence>
          {!loaded && (
            <motion.div
              key="skeleton"
              initial={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 skeleton"
            />
          )}
        </AnimatePresence>

        {/* Screenshot image — loaded directly from ScreenshotOne by the browser */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={screenshotUrl}
          alt={`Screenshot of ${targetUrl}`}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
          className={`w-full h-full object-cover transition-opacity duration-500 ${
            loaded ? "opacity-100" : "opacity-0"
          }`}
        />
      </div>

      <p className="mt-2 text-text-muted text-xs truncate">Preview: {targetUrl}</p>
    </div>
  );
}
