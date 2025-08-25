Goals:
Phase 1:
- [x] Accept user defined module spider, container data, and parsed csv location
- [x] Implement parsing module spider information
  - [x] Implement parsing module spider information based on user defined regex
- [x] Implement adding already parsed information from csv file
- [x] Add parsing support for container definition files
- [x] Allow users to show information obtained strictly from their module spider information or our database
- [x] Implement a way for users to view reports on the website
 - [x] Users should be able to mark reports as addressed or completed
- [x] Users should be able to specify a limited set of styles
 - [x] Users should be able to choose the primary color for the website
 - [x] Users should be able to specify the overall name for the website
- [x] Users should be able to rename columns
- [x] users should be able to reorder columns

Phase 2:
- [ ] Create a docker image to host the code and any files
- [x] Implement a way for users to request some software be covered by our database.
  - [ ] Direct users to where they can request an api key for our database
  - [x] Use their api key to send the request
  - [ ] Curated information and vetted ai information will be added to the database
  - [ ] If software is too specific to a specific cluster and not used in the HPC field or any broad research field then we might not cover that software
  - [ ] Once the database is updated, they will get the information when they next sync their local database (done automatically or manually)
    - [ ] Implement a way for users to automatically sync their local info with our local database info
- [ ] Figure out what to do about duplicate software names
  - Currently softwares are treated as unique if they have different names. Multiple softwares may have the same name... figure it out.
  - [ ] Implement software name alias.
    - In cases where the user wants to keep a specific software name, they should be able to attach an alias to that name. So the front end will show the user provided software name but our internal logic will match on either the alias or software name. Basically, user gets to keep their software name `anysys/fluent`, `container/r`, `conda/R` and that is what will be shown in the software column but the api columns will base their information on the alias the user provides `fluent`, `r`, `r` in this example.
    - In cases where there are multiple software with the same name, we will internally give one of those software a unique alias. so we can store both the actual name of the software but also its unique descriptions, links etc.
    - TODO: flesh out this system more. Which one takes priority? How do we make sure our 'unique' alias is not already a software that exists or will exist?
- [ ] Define a set of standard comments for container (.def) files that our parser can easily read.

Future Plans:
- [ ] Anyone (regardless of if they are using the external SDS tool or not)  will have an option to
share their module spider information with us (to be sorted in our database so that it helps future users
and so that we can generate the necessary information)
- [ ] All information collected about software, versions, HPC centers, etc. may at
some point in the future be displayed publicly or privately to help the broader HPC community
 - [ ]  If information is to be displayed publicly then users will be able to opt out. (They can still share it with us but it won’t be public)
- Currenlty the website is running on its own server. Users may want to integrate SDS into their existing websites... Is this something we want to support?
Bugs:
- [ ] Column widths are not dispalyed properly when not using API info
