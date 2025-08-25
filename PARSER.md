# Table of Contents
- [Parsing `module spider`](#parsing-module-spider)
  - [Spack specific parsing](#spack-specific-parsing)
  - [Custom parsing function](#custom-lmod-parsing-function)
  - [Detailed explanation of regex](#detailed-explanation-of-regex)
- [Parsing `container definitions`](#parsing-container-definitions)
  - [Only parse SDS comment block](#Only-parse-SDS-comment-block)

# Parsing `module spider`

This application parses the output of the `module spider` command. The `module spider` command is from the [lmod package](https://lmod.readthedocs.io/en/latest/index.html). The parser expects a text file.
So, technically, any text file with the same format will work.

The existing parsing script is for data in the following format: `  software: software/version` or `  software-name: software-name/version` or `  software_name: software_name/version` (note the leading two spaces).

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
### Spack specific parsing
If you are using `spack` to create modules, you should use the following config:
```
parsing:
  lmod_spider:
    version_cleaner: '/|-(?=\d)'
    name_pattern: '(.*?)-(\d.*?)'
    spider_description_separator: '----'
```
It will parse like so:
```
  cairo-1.16.0-gcc-9.3.0-fmtofpt: cairo-1.16.0-gcc-9.3.0-fmtofpt
software: cairo version: 1.16.0-gcc-9.3.0-fmtofpt

  cmake: cmake/3.19.4
software: cmke, version: 3.19.4
```
Note that the regex above parses both normal lmod and spack moduel names

### Custom Lmod Parsing Function
Note that `custom_name_version_parser` cannot be passed in in the `config.yaml` file.
Modify the `custom_lmod_parser` function in `parsers/lmod/custom_parsers/custom_lmod_parser.py` with your custom logic.
Here is what the predefined function looks like:
```
def custom_lmod_parser(name: str, versions: list[str], software_info: list[dict]):
    """
    Define your custom parsing function here.
    Change the values of name and versions as necessary

    Args:
        name (str): software name identified by the parser
        version (list): list of versions identified by the parser
        software_info (dict): list of dictionaries containg 'name', 'versions', and 'discription'
            of all software in current file

    Return:
        name (str): software name identifed by custom parser
        version (list): list of versions identified by the custom parser
        software_info (dict): list of dictionaries containg 'name', 'versions', and 'discription'
            of all software in current file (optionally modifed by the custom parser)
    """
    # pp(name)
    # pp(versions)
    # pp(software_info)
    return name, versions, software_info

```

### Detailed explanation of regex
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
> name_version: `autotools: autotools/1.2`\
> Sections: `autotools`, ` autotools/1.2`\
> name_version: `ant/1.10.7: ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`\
> Sections: `ant/1.10.7`, ` ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`\
> name_version: `dir/r: dir/r/3.5.2`\
> Sections: `dir/r`, ` dir/r/3.5.2`

The `name_pattern` will group items separated by a slash. The parser uses the first group as the software name.
> **NOTE**: Example Sections\
> name: `autotools`\
> parsed_name: `autotools`\
> name: `ant/1.10.7`\
> parsed_name: `ant`\
> name: `dir/r`\
> parsed_name: `dir`

`Version_separator` tells the parser what separates each version (almost always a comma)
> **NOTE**: Example Sparation\
> version: ` autotools/1.2`\
> separated version: [`autotools/1.2`]\
> version: ` ant/1.10.7/hcgc7fk, ant/1.10.7/5soub24`\
> separated version: [`ant/1.10.7/hcgc7fk`, `ant/1.10.7/5soub24`]\
> version: ` dir/r/3.5.2`\
> separated version: [`dir/r/3.5.2`]

`Version_cleaner` tells the parser to split each separated version based on some character. It only splits on the first matched character and the rest is treated as the version
> **NOTE**: Example Clean\
> version: [`autotools/1.2`]\
> cleaned version: [`1.2`]\
> version: [`ant/1.10.7/hcgc7fk`, `ant/1.10.7/5soub24`]\
> cleaned version: [`1.10.7/hcgc7fk`, `1.10.7/5soub24`]

`custom_name_version_parser` allows the user to define a custom python function for parsing the name and version.
To implement this you will have to edit the `custom_name_version_parser` function found in `parsers/lmod/parse_spider.py`.

# Parsing `container definitions`

The container parser will attempt to automatically get all the software installed from the definition file.
Sometimes the parser can miss some software. If you want to make sure a particular software/version is captured,
add the follow section to the **bottom** of your definition file:
```
## SDS Software
#	software1/version
#	software2
```

You can also specify the container file and definition (docker) file locations as well as commands to run particular software like so:
```
## SDS Software
# container_file: /path/file.sinf
# def_file: /path/dir/dockerfile
#	software1/version
#	software2: command for sofwtare 2
```

Note the leading `## SDS Software` which lets the parsers know to specifically look for data there.\
For the container and definition (docker) file paths, they must have `# container_file` or `#def_file` followed by a colon `:` followed by the file path.\
For the software, the content to the left of the  `/` will be treated as the software name; the content to the right, the version. Similar to container and def_file, the colon `:` is used to identify the command for a prticular software. Content to the left of the colon is used to identify the software and version and content to the right is used to identify the software.

You can add as many software below it as you want, just make sure that there is one leading comment character such as `#`.\


Currently, the container parser will ignore all url links. This is by design as there is no set standard for how urls are named, and so it is difficult to get relevant data from them.

The parser will automatically obtain everything in the help (`%help`) section of the definition file.
This data is then added to the "Notes" section of each container entry.

Here are some example definition file:
```
BootStrap: docker
From: nvidia/cuda:8.0-devel-ubuntu16.04

%post
    apt-get -y update
    apt-get -y install git vim wget sudo
    git clone https://github.com/torch/distro.git /torch --recursive
    cd /torch;
    sed 's/sudo/ /g' install-deps > install-deps_no_sudo
    bash install-deps_no_sudo;
    ./install.sh
    /torch/install/bin/luarocks install torch
    /torch/install/bin/luarocks install nn
    /torch/install/bin/luarocks install image
    /torch/install/bin/luarocks install lua-cjson
    /torch/install/bin/luarocks install https://raw.githubusercontent.com/qassemoquab/stnbhwd/master/stnbhwd-scm-1.rockspec
    /torch/install/bin/luarocks install https://raw.githubusercontent.com/jcjohnson/torch-rnn/master/torch-rnn-scm-1.rockspec
    /torch/install/bin/luarocks install cutorch
    /torch/install/bin/luarocks install cunn
    git clone https://github.com/jcjohnson/densecap.git /densecap


## SDS Software
# container_file: /path/file.sinf
# def_file: /path/dir/dockerfile
#	torch
#   densecap/latest
```
Since the `densecap` software is installed using a url, it would normally not be captured by the parser,
but with the `## SDS Software` comment, it will find the two software `torch` and `densecap`. `torch` will
not have a version but `densecap` will have the version `latest`.

### Only parse SDS comment block
You can tell the parser to only parse the "SDS software" comment block rather than parsing the entire definition/docker file. Add the following to your `config.yaml` file:
```
parsing:
  container:
    comment_block_only: True
```

Here is what an example config file might look like:
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
  container:
    comment_block_only: True
```

Further customization for the definitaion file parser may be added in the future.
