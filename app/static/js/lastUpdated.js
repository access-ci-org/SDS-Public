/*//////////////////////////////////////////////////////////////////////////////
    This is a script to display on the website when it was last updated //
*///////////////////////////////////////////////////////////////////////////////

$(document).ready(function() {
    console.log("Document is ready");
    
    $.ajax({
        url: '/static/last_updated.txt',
        success: function(data) {
            console.log("Data fetched: ", data);
            
            var lastUpdatedDate = new Date(data.trim());
            console.log("Parsed date: ", lastUpdatedDate);
            
            if (!isNaN(lastUpdatedDate.getTime())) {
                var options = { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true, timeZoneName: 'long'};
                var formattedDate = lastUpdatedDate.toLocaleString('en-US', options);
                console.log("Formatted date: ", formattedDate);
                
                document.getElementById("lastUpdated").innerHTML = formattedDate;
            } else {
                console.log("Invalid date format");
                document.getElementById("lastUpdated").innerHTML = "Invalid date format.";
            }
        },
        error: function() {
            console.log("Error fetching the date");
            document.getElementById("lastUpdated").innerHTML = "Unable to fetch last updated date.";
        }
    });
});
