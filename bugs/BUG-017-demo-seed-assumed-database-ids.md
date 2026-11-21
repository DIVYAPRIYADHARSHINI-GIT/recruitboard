# BUG-017 — Demo seed assumed users/jobs/reasons started at ID 1

Found during Vercel preparation on 21 November 2026 by reviewing initialization for a database that may already have attempted startup. The seed referenced literal user/interviewer/reason/job IDs instead of the rows actually inserted. Database sequences need not start at 1, especially after PostgreSQL transaction rollbacks. It also checked only the user table before seeding, rather than refusing existing business records.

A new isolated SQLite regression assigned generated user/job IDs starting at 100/200 and shifted rejection-reason IDs. The unmodified seed reproduced a FOREIGN KEY constraint failure while inserting an application. The real failed-test transcript is retained at `bugs/20261121-153823-978203-seed-offset-regression-before-fix.txt`; SQL parameters were hidden. No production database or candidate data was accessed.

Fix: retain inserted ORM row objects and use their actual IDs for every reference; query active reason IDs; seed only when users/jobs/candidates/applications are all empty. Tests cover shifted IDs, repeat safety and refusing a nonempty business database.

This is a reproduced local code defect. It is **not confirmed as the cause of the earlier Render exit-status-1 failure**, because that deployment's traceback has not been supplied. Do not relabel BUG-014 as fixed based on this inference. A post-fix local suite verifies the correction before the authorized Vercel deployment attempt.