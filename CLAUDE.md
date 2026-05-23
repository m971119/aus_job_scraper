## Business Requirements
- A web application that scrapes and logs recent jobs from seek
- Website origin: seek.com.au, linkedin
- Please use playwright tool to scrape jobs from seek
- Login using the email and password from .env, make sure to save session cookies so it doesn't login every round
- Before saving the job to DB, do a search first to existing DB to prevent duplicates, if a job is listed on a different date, insert a  indicating duplicate posts 


## Technical Details

- Implemented as a modern NextJS app, client rendered
- The NextJS app should be created in a subdirectory `frontend`
- The backend should be written in python using FastAPI
- Everything packaged into a Docker container
- Use SQLLite as Database, preserve the data when docker container stops
- Use `uv` as the package manager for python in the Docker container
- Start and Stop server scripts for Mac, PC, Linux in `scripts/`
- No user management for the MVP
- Use popular libraries
- As simple as possible but with an elegant UI

## Database tables and columns
> Note: add more tables, columns or redesign the schema if you feel necessary
1. Jobs
    - state
    - city
    - suburb
    - listed dates (plural since the same job might be listed multiple times)
    - seek page url
    - job title
    - job description
    - salary range


## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Strategy

1. Write plan with success criteria for each phase to be checked off. Include project scaffolding, including .gitignore, and rigorous unit testing.
2. Execute the plan ensuring all critiera are met
3. Carry out extensive integration testing with Playwright or similar, fixing defects
4. Only complete when the MVP is finished and tested, with the server running and ready for the user

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.