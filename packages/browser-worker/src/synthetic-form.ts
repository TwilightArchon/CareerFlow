export const SYNTHETIC_FORM_URL = 'https://synthetic.careerflow.invalid/application';

export const SYNTHETIC_FORM_HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'none'">
    <title>CareerFlow Safe Autofill Lab</title>
    <style>
      :root { color: #19211d; background: #f2f3ef; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
      body { margin: 0; padding: 48px 24px; }
      main { width: min(760px, 100%); margin: auto; background: #fffdfa; border: 1px solid #d9ddd7; border-radius: 18px; padding: 34px; box-shadow: 0 18px 60px rgba(30, 50, 40, .1); }
      .badge { display: inline-block; padding: 5px 9px; border-radius: 999px; color: #73541f; background: #f7ecd0; font-size: 12px; font-weight: 750; }
      h1 { margin: 14px 0 8px; font-family: Georgia, serif; font-weight: 500; }
      p { color: #647169; line-height: 1.5; }
      .notice { border-left: 4px solid #3d8a68; padding: 10px 14px; background: #edf5f0; }
      fieldset { border: 0; padding: 0; margin: 28px 0; }
      legend { width: 100%; border-bottom: 1px solid #e4e6e1; padding-bottom: 9px; font-weight: 750; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
      label { display: grid; gap: 6px; color: #354139; font-size: 13px; font-weight: 700; }
      input, select { width: 100%; box-sizing: border-box; border: 1px solid #cbd1cb; border-radius: 8px; padding: 11px; font: inherit; background: white; }
      [data-careerflow-filled='true'] { border-color: #3d8a68; background: #edf7f1; box-shadow: 0 0 0 3px #dceee4; }
      .review { color: #835b1d; background: #fbf1dc; border-radius: 10px; padding: 12px; font-size: 13px; }
      button { border: 0; border-radius: 9px; padding: 12px 18px; font-weight: 750; background: #a8b2ad; color: white; }
      @media (max-width: 620px) { .grid { grid-template-columns: 1fr; } main { padding: 24px; } }
    </style>
  </head>
  <body>
    <main>
      <span class="badge">LOCAL TEST FORM · NO EMPLOYER CONNECTION</span>
      <h1>CareerFlow Safe Autofill Lab</h1>
      <p class="notice">This built-in page tests scanning and policy-controlled filling. It cannot submit an application or send data anywhere.</p>
      <form>
        <fieldset>
          <legend>Candidate</legend>
          <div class="grid">
            <label for="first-name">First name<input id="first-name" name="first_name" autocomplete="given-name" required></label>
            <label for="last-name">Last name<input id="last-name" name="last_name" autocomplete="family-name" required></label>
            <label for="email">Email address<input id="email" name="email" type="email" autocomplete="email" required></label>
            <label for="phone">Phone number<input id="phone" name="phone" type="tel" autocomplete="tel"></label>
            <label for="linkedin">LinkedIn profile<input id="linkedin" name="linkedin" type="url"></label>
            <label for="github">GitHub profile<input id="github" name="github" type="url"></label>
          </div>
        </fieldset>
        <fieldset>
          <legend>Education</legend>
          <div class="grid">
            <label for="school">School or university<input id="school" name="school" autocomplete="organization"></label>
            <label for="degree">Degree<input id="degree" name="degree"></label>
            <label for="field-of-study">Field of study<input id="field-of-study" name="field_of_study"></label>
            <label for="graduation-year">Graduation year<input id="graduation-year" name="graduation_year" inputmode="numeric"></label>
          </div>
        </fieldset>
        <fieldset>
          <legend>Questions requiring human review</legend>
          <div class="grid">
            <label for="work-authorization">Work authorization<select id="work-authorization" name="work_authorization" required><option value="">Choose…</option><option>Yes</option><option>No</option></select></label>
            <label for="sponsorship">Will you require sponsorship?<select id="sponsorship" name="sponsorship" required><option value="">Choose…</option><option>Yes</option><option>No</option></select></label>
          </div>
        </fieldset>
        <p class="review">CareerFlow intentionally leaves contact and legal fields for review in this milestone. Submission is disabled.</p>
        <button type="button" disabled>Submission disabled in safe lab</button>
      </form>
    </main>
  </body>
</html>`;
