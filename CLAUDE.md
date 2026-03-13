This directory contains an archive of a Twitter account's tweets.

The tweets are stored in a JavaScript file named `tweets.js`.

Our goal is to generate a static website from the tweets data.

There is a Python script named `generate.py` that reads the tweets
from `tweets.js` and generate a static website in the `output` directory.

Things mostly work correctly. We're going to fix some remaining issues.

Notable files:

 - `tweets.js` - the input data file containing the tweets in JavaScript format.
   - Treat this as READ-ONLY. Don't modify this file.
 - `generate.py` - the Python script that reads `tweets.js` and generates the static
   - This is the file you'll be modifying the most.
 - `static/` - the directory containing static assets like CSS and JavaScript for the generated website.
   - These are files used by the generated website. You can modify these.
 - `output/` - the directory where the generated static website is stored.
   - This is the output of the `generate.py` script. Contents here will be overwritten when you run `generate.py` again.

How to generate the static site:

    python3 generate.py

Once you've read this file, tell me by saying "I've read the CLAUDE.md file. Let's get started!"
