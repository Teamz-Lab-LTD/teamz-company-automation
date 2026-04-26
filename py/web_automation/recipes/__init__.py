"""Recipes — each module here automates one site/task.

Conventions:
  * One module per site or task.
  * Module exports either a top-level `Recipe` class or a factory
    `build_recipe(args)` + `add_args(parser)` pair.
  * All recipe data (yaml, json, csv) lives in the host project's
    `automation_data/` folder, NOT in this submodule.

Built-in recipes:
  * play_console_icons — bulk-upload icons to Play Games achievements
  * blogger_post       — draft + publish posts on Blogger.com
  * reddit_comment     — post comments on a list of Reddit threads
  * generic_form_fill  — fill arbitrary forms from a yaml config
"""
