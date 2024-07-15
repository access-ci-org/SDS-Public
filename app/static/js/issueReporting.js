/*//////////
  Imports //
*///////////
import { showAlert, hideAlert } from './alerts.js';
import { staticTable } from './table.js';

/*///////////////////
  Global Variables //
*////////////////////
var issueReport = {}        // Report Object
var reportingIssue = false; // State Controller
var selectedElement = null; // Event Target

/*////////////
  Functions //
*/////////////

// EVENT HANDLERS //
////////////////////

//function handleClick(event){}
// Mouse Click Event Listener
// This functionality is implemented elsewhere now

function handleMouseMove(event)
// Mouse Movement Event Listener
{
  var target = event.target;  // Assigns the Element underneath the Mouse Cursor to Target

  if (selectedElement && selectedElement !== target)  // If there is already a Target, and it is not the current Target
                                                      // i.e. the Mouse Cursor has moved somewhere else on the page
  {
      selectedElement.classList.remove('hovered');    // Remove the red Target outline from the previous Target
  }

  // If Cursor highlights a valid Table Cell ('td')
  if (target.tagName.toLowerCase() == 'td')
  {
    target.classList.add('hovered');  // Draw the red Target outline around Target
    selectedElement = target;         // Store reference to Target in Global Variable selectedElement
  }
  else
  {
    selectedElement = null; // Remove Target reference if Mouse leaves the Table
                            // This prevents generating reports unless you click directly on the cell
  }
}

function handleKeyDown(event)
// Keyboard Key Event Handler
{
  if (reportingIssue && event.key === 'Escape')
  {
    exitReportingState();
  }
}

// BEHAVIORS //
///////////////

function enterReportingState()
// Begin 'Report Issue' Subroutine
{
  // Set Reporting State
  reportingIssue = true;
  
  // Alert User (from ./alert.js)
  var alertDivMessage = "Please click on the cell in the table where there is an issue.";
  var alertType = 'info';
  showAlert(alertDivMessage, alertType);

  // Prepare Reporting State
  $("#reportIssueText").text('Cancel');           // Change 'Report Issue' buutton text to 'Cancel'
  $('body').css('cursor', 'crosshair');           // Change Mouse cursor type to 'Crosshair'
  $('body').on('click', handleIssueReportClick);  // Enable 'handleIssueReportClick' Event Listener
  $('body').on('mousemove', handleMouseMove);     // Enable 'handleMouseMove' Event Listener
  //$(document).on('click',handleClick);          // Enable 'handleClick' Event Listener (Currently Unnecessary)
  $(document).on('keydown',handleKeyDown);        // Enable 'handleKeyDown' Event Listener
  
  // Disable selecting rows while reporting
  staticTable.select.style('api');  
}

function exitReportingState()
// End 'Report Issue' Subroutine
// Reset Event Handler States to Default After Report
{
  // Variables
  reportingIssue = false; // Return Reporting State to Default (Off)
  if (selectedElement)    // If a target was previously selected (Red Outline)
  {
    selectedElement.classList.remove('hovered');  // Remove 'hovered' status, which draws the red Target outline
    selectedElement = null;                       // Remove stored reference to Target
  }

  // Scripts
  $("#reportIssueText").text('Report Issue');     // Set 'Report Issue' button text back to default (from 'Cancel')
  $('body').css('cursor','default');              // Return Cursor Style back to 'default' (From 'Crosshair')
  $('body').off('click',handleIssueReportClick);  // Disable 'handleIssueReportClick' Event Listener
  $('body').off('mousemove', handleMouseMove);    // Disable 'handleMouseMove' Event Listener
  //$(document).off('click',handleClick);         // Disable 'handleClick' Event Listener 
                                                  //   Remember to renable this too if implementing handleClick again
  $(document).off('keydown',handleKeyDown);       // Disable 'handleKeyDown' Event Listener
 
  // Alert
  hideAlert();

  // Renable selecting rows once report is done
  staticTable.select.style('multi'); 
}

function handleIssueReportClick(event)
// Behavior of 'Report Issue' Button
{
  event.preventDefault();   // Prevents the default behavior of what is clicked (in this case, preventing links from being opened while in 'Reporting' State)
  if (selectedElement.tagName.toLowerCase() == 'td')  // If Targeted Element is a valid cell in the Table
  {
    event.stopPropagation();  // Prevents Event Propagation, meaning one Event (in this case, clicking) will not trigger other Event Listeners
    $('body').off('mousemove', handleMouseMove); // Disable 'handleMouseMove' event (i.e. Stop drawing outline/don't update Target)

    // Prepare Page URL
    var pageUrl = window.location.href;

    // Capture Table Metadata                  
    var elementType = selectedElement.tagName.toLowerCase();
    //var elementId = selectedElement.id;                       // Do we have unique IDs per element?                   
    var elementClass = selectedElement.className;
    var elementText = $(selectedElement).text().trim();       // Content of Target Element, Trimmed of Whitespace

    // Prepare an Object to capture Table Cell information
    var tableCellInfo = {};

    // Capture Cell Metadata
    var $cell = $(selectedElement);
    var $row = $cell.closest('tr');
    var $table = $row.closest('table');

    // Stage Cell Metadata 
    var tableId = $table.attr('id');
    var rowIndex = $row.index();
    var columnIndex = $cell.index();
    var rowName = $row.find('td:first-child').text().trim();
    var columnName = $table.find('th').eq(columnIndex).text().trim();  // Table headers are in <th> elements

    // Create a tableCellInfo Object
    tableCellInfo = 
    {
        tableId: tableId,
        rowIndex: rowIndex,
        columnIndex: columnIndex,
        rowName: rowName,
        columnName: columnName
    };

    // Create an issueReport Object from Table Metadata and Cell Metadata
    issueReport = 
    {
      pageUrl: pageUrl,
      elementType: elementType,
      //elementId: elementId,
      elementClass: elementClass,
      elementText: elementText,
      tableCellInfo: tableCellInfo,
    };

    // Create a formatted string for the report details
    var reportDetails = 
      "Page URL: " + issueReport.pageUrl + "\n" +
      "Element Type: " + issueReport.elementType + "\n" +
      //"Element ID: " + issueReport.elementId + "\n" +
      "Element Class: " + issueReport.elementClass + "\n" +
      "Element Text: " + issueReport.elementText + "\n" +
      "Table Cell Info: " + JSON.stringify(issueReport.tableCellInfo, null, 2);
    
    // Place reportDetails Object information into reportDetails Element
    $("#reportDetails").text(reportDetails);

    // Display Modal containing reportDetails element
    $("#report-modal").modal('show');

    // Finish Reporting Routine
    exitReportingState();
  }
}

/*//////////
  BUTTONS //
*///////////

// 'Report Issue' Button
// Modal defined in 'reportModal.html'
$("#reportIssueBtn").on('click',function(event)
{
  if (!reportingIssue) // Toggle Reporting State On
  {
    enterReportingState();
  } 
  else                // Toggle Reporting State Off
  {
    exitReportingState();
  }
}
);

// 'Send Report' Button
// >Inside 'Report Issue' Modal
$("#sendReportBtn").on('click', function() 
{
    var userForm = $('#reportFeedback').val();

    // In jQuery, AJAX exchanges data with a server
    // In this case, we're packaging the bug report and sending it to our server for manual review
    $.ajax(
    {
      url: '/report-issue',                                                         // Where the report goes (server endpoint)
      type: 'POST',                                                                 // POST-request: data sent TO server (create or update)
      data: JSON.stringify({ formReport: userForm, reportDetails: issueReport }),   // Combining everything into a JSON file { field: value }
      contentType: 'application/json',                                              // Telling the server to expect a JSON file
      success: function(response) 
      {
        $('#report-modal').modal('hide');
        showAlert('Issue reported successfully!', 'success');
        // Clear Objects
        issueReport = {};
        $("#reportDetails").text(' ');
      },
      error: function(xhr, status, error) 
      {
        console.error('Error reporting issue:', error);
        showAlert('Failed to report issue. Please try again.', 'danger');
      }
    });
});

// 'Provide Feedback' Button
// Modal defined in 'feedbackModal.html'
$("#provideFeedbackBtn").on('click', function() 
{
  $("#feedback-modal").modal('show');
}
);
  
// 'Submit Feedback' Button
// >Inside 'Provide Feedback' Modal
$("#sendFeedbackBtn").on('click', function() 
{
  var userFeedback = $("#provideFeedback").val();

  $.ajax(
  {
    url: '/user-feedback',
    type: 'POST',
    data: JSON.stringify({ feedbackForm: userFeedback }), // There's no cell data for this report, only what the user types into the form
    contentType: 'application/json',
    success: function(response) 
    {
      $("#feedback-modal").modal('hide');
      showAlert('Feedback reported successfully!', 'success');
    },
    error: function(xhr, status, error) 
    {
      console.error('Error sending feedback:', error);
      showAlert('Failed to send feedback. Please try again.', 'danger');
    }
  });
});