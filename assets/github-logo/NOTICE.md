# The GitHub mark — what GitHub actually says, and why this directory is empty

The map carries a node for GitHub's repository and Actions. It currently draws a
project glyph rather than GitHub's mark, and this file records why, and what the
terms are, so the question does not have to be re-asked from memory later.

## What GitHub says

Read from <https://brand.github.com/foundations/logo> (reached by redirect from
<https://github.com/logos>), in Phase 20a, for the same reason ADR-0039 gave for
the AWS icons: establish the terms from the vendor rather than guess.

```text
permitted
  "Use a permitted GitHub logo to link to GitHub."
  "Use a permitted GitHub logo to inform others that your project integrates
   with GitHub."
  "Use the GitHub logo in a blog post or news article about GitHub."
  "Use the permitted GitHub logos less prominently than your own company or
   product name or logo."

not permitted
  "Do not use the GitHub name or any GitHub logo in a way that suggests you are
   GitHub, your offering or project is by GitHub, or that GitHub is endorsing
   you."
  "Do not use any GitHub logo as the icon or logo for your business/organization,
   offering, project, domain name, social media account, or website."
  "Do not modify the permitted GitHub logos, including changing the color,
   dimensions, or combining with other words or design elements."
```

## The difference from the AWS answer, which is the point of writing it down

AWS's three pages **neither permit nor exclude** a public web page, so
`assets/aws-icons/NOTICE.md` records a decision taken in the absence of a "no".
GitHub's page **names this case and permits it**: a mark on a node that says
"this project's pipeline runs on GitHub Actions" is "inform others that your
project integrates with GitHub", and one small node icon beside the project's own
heading is "less prominently than your own product name".

Two vendors, two different kinds of answer. Recording only the conclusion would
have lost that, and the next person would have assumed the AWS reasoning applies
here too.

## Why the directory is empty

The mark may not be modified, and it may not be recreated by hand — a redrawn
Octocat is a modified one. The official asset has to be downloaded from
<https://brand.github.com>, which is a step that belongs on a machine with the
browser, not in a generator. Until it is here, the node carries the project glyph
`CI`, which claims nothing.

When the file arrives it goes in beside this one, unmodified, and its key is
added to `KEYS` in `scripts/build-icon-sprite.py` and to `AWS_ICON`'s sibling set
in the page — note that the sprite's `.icon.aws` styling and the AWS/glyph split
in the template are named after AWS and would need a third case, because GitHub
is neither an AWS service nor a project glyph.
