import React, { useState } from "react";

const ReportModal: React.FC = () => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="overlay panel-bottom-right">
        <button className="btn-report" id="btn-report" onClick={() => setOpen(true)}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Report Incident
        </button>
      </div>

      {open && (
        <div className="modal-backdrop" id="report-modal">
          <div className="modal" style={{ position: "relative" }}>
            <button className="modal-close" id="modal-close" onClick={() => setOpen(false)}>
              &times;
            </button>
            <h2>Report Incident</h2>
            <p className="modal-sub">
              Submit a suspected phishing link or message for AI analysis
            </p>

            <form
              id="report-form"
              onSubmit={(e) => {
                e.preventDefault();
                // Optional: wire this to a backend endpoint if needed
                setOpen(false);
              }}
            >
              <div className="form-group">
                <label htmlFor="report-link">Suspicious Link / Message</label>
                <textarea
                  id="report-link"
                  name="link"
                  placeholder="Paste the suspicious URL or message..."
                  required
                ></textarea>
              </div>

              <div className="form-group">
                <label htmlFor="report-type">Attack Type</label>
                <select id="report-type" name="type">
                  <option value="sms">SMS Phishing</option>
                  <option value="email">Email Phishing</option>
                  <option value="url">Malicious URL</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="report-location">Location</label>
                <select id="report-location" name="location">
                  <option value="dehradun">Dehradun</option>
                  <option value="haridwar">Haridwar</option>
                  <option value="rishikesh">Rishikesh</option>
                  <option value="haldwani">Haldwani</option>
                  <option value="nainital">Nainital</option>
                  <option value="uttarkashi">Uttarkashi</option>
                  <option value="pithoragarh">Pithoragarh</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <button type="submit" className="btn-submit">
                Submit for Analysis
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default ReportModal;

