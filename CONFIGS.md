This page will go over all config options avaible for the SDS

# Adding configs

Create a `config.yaml` file in the project folder and add any configs there.

Each category presented below (api, styles, etc.) will have multiple things that can be
modified. Each should be in its own field with subfields for each configuration. Examples
are provided below for each category and at the bottom of the page you can find an example
file using all categories (but not all configs)

# Available Configs

## API configs
Used to deffine API keys and data to be used from the sds API
```
api:
  use_api: False
  api_key: "your api key here"
  use_curated_info: False
  use_ai_info: False
```

- `user_api`: Set `use_api` to `True` to connect to a remote SDS database (using the `sds_api_key`). Default: False
- `api_key`: Set `api_key` API key to the sds website, you can obtain one here: (link to website or email of people to contact)
- `use_curated_info`: Set `use_curated_info` to `True` to display curated information (such as software descriptions, link to software webpage, etc). If no software descriptions are provided and `use_curated_info` is set to true then it will use informaton from the api call to add descriptions. Default: False
- `use_ai_info`: Set `use_ai_info` to `True` to display AI generated information (such as AI descriptions, Software example use, etc.) on your website. Default: False

## Style Configs
Used for setting styles like colors, logo, title, etc.
```
styles:
  primary_color: "your primary color here"
  secondary_color: "your secondary color"
  site_title: "Title for website here"
  logo: "logo file name"
```
- `primary_color`: Set `primary_color` and `secondary_color` to set the colors (in hexadecimal, e.g. #1B365D) for the website. Different shades of these two colors are used in the website. Darker, monochromatic, colors are recommended. Default Primary: #1b365d, Default Secondary: #324a6d
- `site_title`: Set `site_title` to be the main title you want for your website. Default: SDS
- `logo`: Set `logo` to be the relative path to the image you want to display as your logo.

## General Configs
General configurations used to define application behaviour.

```
general:
  user_name: default admin user
  password: default admin password
  share_software: False
  show_container_page: True
  drop_columns: []
  ifram: False
```
- `username`: Set `user_name` to be the default admin user for your website

- `password`: Set `password` to be the password for that default user

- `share_software`: Set `share_software` to be `True` if you want to share the names of the software available on your resources with us. This inforamtion will be used to identify software for which we need to collect more data. Default is `False`.

- `show_container_page`: Set `show_container_page` to be `False` if you don't want the container page to be accessible. Default is `True`

- `drop_columns`: Set `drop_columns` to be a list of columns (or displayed data in the 'Details' modal) i.e. `['column_name1', 'column_name2']` if you don't want certain columns (or data) to be visible. Column names that have a ✨ should have 'AI' in front of the column name (e.g: to disable the 'Tags ✨' column, use 'AI Tags'). Default is `[]`

    - Here is the full list of available columns: `['Software', 'Resource', 'Containers',
        'Description' 'AI Description', 'Versions', 'AI Software Type', 'AI Software Class',
       'AI Research Field', 'AI Research Area', 'AI Research Discipline',
       'AI Core Features', 'AI Tags', 'Software's Web Page',
       'Software Documentation', 'Example Software Use', 'AI Example Use',
       'Command']`
    - Note that some columns have been combined on the website for display, you may have to remove
        multiple of similar columns to get the intended effect
    - Also note, just because you can remove some columns doesn't mean you should, removing some
        combination of columns may have unintended effects

- `iframe`: Set `iframe` to be `True` if you are showing this page using an iframe. This will just remove the header and title of the page. Default is `False`

## Parser Configs
This set of configs can be used to control how the sds parser parsers your data.
```
parsing:
  lmod_spider:
    section_separator: '\n(?=\s{2}[/\w.+-]+(?:/[\w+\-])*:)'
    name_version_pattern: '([/\w.+-]+(?:-[/\w+\-]+)?): (.+)'
    version_separator: '[,]'
    name_pattern: '(.+)' # this basically disables the name_pattern match
    spider_description_separator: '----'
  container:
    comment_block_only: True
```

See the *`PARSER.md`* file for details about the what the configs do.
