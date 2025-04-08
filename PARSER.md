# Table of Contents
- [Parsing `module spider`](#parsing-module-spider)
- [Parsing `container definitions`](#parsing-container-definitions)

# Parsing `module spider`

This application parses the output of the `module spider` command. The `module spider` command is from the [lmod package](https://lmod.readthedocs.io/en/latest/index.html). The parser expects a `.txt` file.
So, technically, any `.txt` file with the same format will work be parsed.

The existing parsing script is for data in the following format: `software: software/version` or `software-name: software-name/version` or `software_name: software_name/version` (note the leading two spaces).

If there is are descriptions for a software then it will be included. If a software appears multiple times then only one instance will be recorded with multiple versions. Below is an example of `module spider` output.

```
$ module spider
--------------------------------------------------------------
The following is a list of the modules currently available:
--------------------------------------------------------------
  autotools: autotools/1.2
    Autoconf, automake, libtool
  boost: boost/1.54.0, boost/1.55.0, boost/1.56.0, boost/1.61.0, boost/1.62.0
  Boost provides free peer-reviewed portable C++ source libraries.
  blast+: blast+/arm21/2.12.0
  blast+: blast+/arm22.0/2.12.0
```

The parser for the `module spider` command takes in seven key arguments:

```
section_separator: Regex pattern to split the file content into sections.
    A section is an entry of software name, versions, and descriptions (if availabe).
    Defaults to '\n(?=\s{2}[\/\w.-]+(?:/[\w-])*:)'.

name_version_pattern: Regex pattern to extract software name and version from section.
    Defaults to '([\w/.-]+(?:-[\w/-]+)?): (.+)'.

name_pattern: Regex pattern to further refine software name.
    Defaults to '([^/]+)(?=/.*)'

version_separator: Regex pattern to split multiple versions.
    Defaults to '[,]'.

version_cleaner: Regex pattern to split version string. Last item from the split will be used
    Defaults to '/'.

spider_description_separator: Separator for spider descriptions.
    Defaults to '----'.

custom_name_version_parser: Custom function to parse
    name and version. If provided, it should accept and return (name, versions, software_info).
    Defaults to None.
```

You can define specific parsing regex in the config.yaml file like so:
```
parsing:
    lmod:
        section_separator: '<custom section_separator>'
        name_version_pattern: '<custom name_version_pattern>'
        name_pattern: '<custom name_patern>'
        version_separator: '<custom version_separator>'
        version_cleaner: '<custom version cleaner>'
        spider_description_separator: '<custom spider_description_separator>'
```
Note that `custom_name_version_parser` cannot be passed in in the `config.yaml` file. How to
specify a `custom_name_version_parser` will be explained at the end of the section.  

Here is what an example `config.yaml` file might look like:
```
api:
  api_key: abcd
  use_api: True
  use_curated_info: true
  use_ai_info: False
styles:
  primary_color: "#1B365D"
  secondary_color: "#1B365D"
  site_title: "A reallly long title like so long that it breaks everything yup its a long title"
  logo: "hi.png"
parsing:
  lmod_spider:
    section_separator: '\n(?=\s{2}[/\w.+-]+(?:/[\w+\-])*:)'
    name_version_pattern: '([/\w.+-]+(?:-[/\w+\-]+)?): (.+)'
    version_separator: '[,]'
    name_pattern: '(.+)' # this basically disables the name_pattern match
    spider_description_separator: '----'
```

The rest of the section will go into a little more detail about each field and how the default selection affects the fields 

`section_separator`, `name_version_pattern`, and `name_pattern` create groups of strings that match the given patterns.

So `section_separator` will group items that:

- begin on a new line `/n`
- have exactly two spaces `\s{2}` followed by some combination of word characters (letters, numbers, underscore, space), /, -, or . (`[\w/.-]+`).
- followed by a colon `:`
- And finally some combination of word characters (letters, numbers, underscore, space), /, -, or . (`[\w/.-]+`)

This will capture everything until it runs into another new line which has the same pattern.  
Using the above example module spider output, here is what the sections would look like:

> **Note**: Example Sections  
> Sections based on parsing the above example `module spider` output  
> Section 1:    
> ```
> autotools: autotools/1.2    
>     Autoconf, automake, libtool
>```  
> Section 2:    
> ```
> boost: boost/1.54.0, boost/1.55.0, boost/1.56.0, boost/1.61.0, boost/1.62.0    
>     Boost provides free peer-reviewed portable C++ source libraries.  
> ```
> Section 3:  
> ```
> blast+: blast+/arm21/2.12.0  
> ```
> Section 4:  
> ```
> blast+: blast+/arm22.0/2.12.0  
> ```

The `name_version_pattern` will do something similar, but in its case it captures everything to the left of the `:` as one group and to the right as another group.
> **Note**: Example Sections
> name_version: `autotools: autotools/1.2`  
> Sections: `autotools`, ` autotools/1.2`  
> name_version: `ant/1.10.7: ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`  
> Sections: `ant/1.10.7`, ` ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`  
> name_version: `dir/r: dir/r/3.5.2`  
> Sections: `dir/r`, ` dir/r/3.5.2`  

The `name_pattern` will group items separated by a slash. The parser uses the first group as the software name.
> **NOTE**: Example Sections  
> name: `autotools`  
> parsed_name: `autotools`  
> name: `ant/1.10.7`  
> parsed_name: `ant`  
> name: `dir/r`  
> parsed_name: `dir`  

`Version_separator` tells the parser what separates each version (almost always a comma)
> **NOTE**: Example Sparation  
> version: ` autotools/1.2`  
> separated version: [`autotools/1.2`]  
> version: ` ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`  
> separated version: [`ant/1.10.7/hcgc7fk`, `ant/1.10.7/5soub24`]  
> version: ` dir/r/3.5.2`  
> separated version: [`dir/r/3.5.2`]  

`Version_cleaner` tells the parser to split each separated version based on some character. It only splits on the first matched character and the rest is treated as the version
> **NOTE**: Example Clean  
> version: [`autotools/1.2`]  
> cleaned version: [`1.2`]  
> version: [`ant/1.10.7/hcgc7fk`, `ant/1.10.7/5soub24`]  
> cleaned version: [`1.10.7/hcgc7fk`, `1.10.7/5soub24`]  

`custom_name_version_parser` allows the user to define a custom python function for parsing the name and version.  
To implement this you will have to edit the `parse_spider.py` file found in `parsers/lmod/`. Define the function in the file.  
Inside the same file in the `parse_spider_output` function, you will see this comment:  
`# lmod_parsing["custom_name_version_parser"] = <your custom function>`  
Uncomment that line and add your function name in place of `<your custom function>`.
# Parsing `container definitions`
Currently, the container parser will ignore all url links. This is by design as there is no set standard for how urls are named, and so it is difficult to get relevant data from them.

In the future, options will be added to allow the user to treat the URLs as a "software" and display them accrodingly.
Further customization for the definitaion file parser may be added in the future.
