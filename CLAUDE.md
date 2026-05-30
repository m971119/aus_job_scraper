## Business Requirements
- A web application that scrapes and logs recent jobs from seek
- Website origin: seek.com.au
- Before saving a job to DB, search for an existing job matching by company + title (case-insensitive) when company is present. If a match is found and the seek_url is new, update the row: append the new url and date, mark the job reposted. Skip if the url already exists.
- Allow users to sort the jobs by latest listing date
- Allow users to view detailed job information
- Allow users to "soft delete/hide" jobs that don't interest them, so that the system may know not to create that job again while scraping in the future.
- Run the scraping job in the background and allow users to view the status of the scraping job in the frontend. The user should know how many pages there are to scrape and which page the job is currently at.
- Allow users to cancel the scraping
- Allow users to add custom tags to each job
- Allow users to fuzzy lookup if the company sponsors



## Technical Details

- Please use playwright tool to scrape jobs from seek
- Implemented as a modern NextJS app, client rendered
- The NextJS app should be created in a subdirectory `frontend`
- The backend should be written in python using FastAPI
- Everything packaged into a Docker container
- Use SQLite as Database, preserve the data when docker container stops
- Use `uv` as the package manager for python in the Docker container
- Start and Stop server scripts for Mac, PC, Linux in `scripts/`
- No user management for the MVP
- Use popular libraries
- As simple as possible but with an elegant UI

## Color Scheme

- Accent Yellow: `#ecad0a` - accent lines, highlights
- Blue Primary: `#209dd7` - links, key sections
- Purple Secondary: `#753991` - submit buttons, important actions
- Dark Navy: `#032147` - main headings
- Gray Text: `#888888` - supporting text, labels

## Bootstrap Strategy

1. Write plan with success criteria for each phase to be checked off. Include project scaffolding, including .gitignore, and rigorous unit testing.
2. Execute the plan ensuring all critiera are met
3. Carry out extensive integration testing with Playwright or similar, fixing defects
4. Only complete when the MVP is finished and tested, with the server running and ready for the user

## Coding standards

1. Use latest versions of libraries and idiomatic approaches as of today
2. Keep it simple - NEVER over-engineer, ALWAYS simplify, NO unnecessary defensive programming. No extra features - focus on simplicity.
3. Be concise. Keep README minimal. IMPORTANT: no emojis ever
4. When hitting issues, always identify root cause before trying a fix. Do not guess. Prove with evidence, then fix the root cause.