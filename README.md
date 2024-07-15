# ACCESS-SDS
Software Documentation Service

## Confluence API
- First, create your API token here: https://id.atlassian.com/manage-profile/security/api-tokens
- Once you have your API token, create a `.env` file in the project folder
- Inside the `.env` file, add the following:  
    `confluence_url = "https://access-ci.atlassian.net"`  
    `confluence_space = "AccessInternalContentDevelopment"`
    `parent_page_id = "245202949"`  
    `atlassian_username = ""`  
    `confluence_token = ""`  
    Replace the empty strings with the appropriate information (**they must be on different lines**).
- That's it you're done!  
