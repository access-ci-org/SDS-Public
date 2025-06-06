import { setupFunctions, updateNavAndHeader } from "./navbarFooter.js";
import { showModalForSoftware, getURLParameter } from "./modals/softwareDetailsModal.js";
import { onExampleUseClick } from "./modals/exampleUseModal.js";

export var staticTable
export var column_names = JSON.parse(col_names) // defined in software_search.html

// Add Navbar, Header, and Footers settings
setupFunctions.universalMenus(document.getElementById("universal-menus"));
setupFunctions.header(document.getElementById("header"));
setupFunctions.siteMenus(document.getElementById("site-menus"));
setupFunctions.footerMenus(document.getElementById("footer-menus"));
setupFunctions.footer(document.getElementById("footer"));

// Update Navbar, Header, and Footer
updateNavAndHeader();

$(document).ready(function()
{
    // Minimum column widths
    const columnWidths = {
        'software_name': '120px',
        'rp_name': '125px',
        'rp_group_id': '175px',
        'software_description': '550px',
        'ai_description': '400px',
        'ai_software_type': '175px',
        'ai_software_class': '175px',
        'ai_research_field': '175px',
        'ai_research_area': '175px',
        'ai_research_discipline': '175px',
        'ai_core_features': '400px',
        'ai_general_tags': '180px',
        'software_version': '160px',
        'software_web_page': '300px',
        'software_documentation': '300px',
        'software_use_link': '300px',
        'rp_software_documentation': '300px',
        'ai_example_use': '175px'
    };

    /*/////////////////////////////////////////////////////////////////////////////////////////////////////////
        STATIC TABLE                                                                                        //
        Enabled: Buttons (Column Visibility), FixedColumn, FixedHeader, SearchPanes, Select //
    *///////////////////////////////////////////////////////////////////////////////////////////////////////

    var staticTable = $('#softwareTable').DataTable({
        select: {           // Allows for selecting rows in tables
            enabled: true,
            style: 'multi', // Select multiple rows, deselect by clicking again
        },
        ordering: false,    // Disables sorting
        fixedColumns: true, // Makes first column 'fixed' to the left side of the table when scrolling
        fixedHeader: true,  // Makes column headers 'fixed' to the top of the table when scrolling
        // autowidth: false,
        // scrollCollapse: true,
        "sScrollX": "100%", // Enables horizontal scrolling
        pageLength: 25,     // Rows displayed per page
        pagingType: 'full_numbers',     // 'First', 'Previous', 'Next', 'Last', with page numbers
        lengthMenu: [                   // User-selectable menu for pageLength
            [10, 25, 50, 250, 500, -1],
            [10, 25, 50, 250, 500, 'All']
        ],
        // DOM: various layout and formatting options.
        // For example: 'p' affects the paging style at the bottom of the table.
        dom: '<"d-flex flex-column flex-md-row justify-content-between"\
                    <"d-flex flex-column flex-md-row"\
                        <"d-flex mb-3 mb-md-0"l>\
                        <"d-flex px-3"B>\
                    >\
                    <"d-flex justify-content-between align-items-center flex-grow-1"\
                        <"d-flex justify-content-start">\
                        <"d-flex scrollText-div">\
                    f>\
                >\
                rt\
                <"d-flex justify-content-between"ip>',
        language: {
            paginate: { // Change Arrows (< and >) into Word Equivalents
                previous: "Prev",
                next: "Next",
                first: "First",
                last: "Last"
            },
            buttons:{   // Rename Column Visibility Buttons
                colvis: 'Show/Hide Columns',
                colvisRestore: 'Restore All'
            },
        },
        buttons: [
            {   // Edit Column Visibility Buttons
                extend: 'colvis',
                collectionLayout: 'two-column',
                popoverTitle: 'Show/Hide Columns',
            },
                'colvisRestore',
        ], 
        stateSave: false,   // Toggle for saving table options between page reloads
        stateDuration:-1,   // How long to save 
        columns: function() {
            var cols = [];
            var headerCells = $('#softwareTable thead th');

            // Create a reverse mapping from display names to internal keys
            const reverseColumnMap = {};
            Object.entries(column_names).forEach(([key, value]) => {
                reverseColumnMap[value] = key;
            });

            headerCells.each(function(index) {
                const displayName = $(this).text().trim();
                const internalKey = reverseColumnMap[displayName];
                var column = {
                    data: internalKey,
                    width: internalKey ? columnWidths[internalKey] : null
                };


                if (internalKey === "software_name") {
                    column.render = function(data, type, row) {
                        if (type === 'display') {
                            return `<a data-bs-toggle="modal" data-bs-target="#softwareDetails-modal" href="#">` + data + '</a>';
                        }
                        return data;
                    };
                } else if (internalKey === 'ai_example_use') {
                    column.render = function(data, type, row) {
                        if (type === 'display') {
                            return '<button class="btn example-use-btn" type="button">Use Example</button>';
                        }
                        return data;
                    };
                } else if (['software_description', 'software_documentation', 
                         'software_web_page', 'software_use_link', 'rp_software_documentation'].includes(internalKey)) {
                    column.render = function(data, type, row) {
                        if (type === 'display' && data) {
                            return makeLinkClickable(data);
                        }
                        return data;
                    };
                }
                cols.push(column);
            });
            return cols;
        }(),
        columnDefs: [
           {
                targets: "_all",
            },
        ],
        initComplete: function() {
            const api = this.api();
            $('.scrollText-div').html("Hover your mouse to the edge of the table to scroll");
        
            // Target the fixed header cells inside the dt-scroll-headInner container.
            // These are the header cells that DataTables displays for scrolling/fixed columns.
            $('.dt-scroll-headInner table thead tr th').each(function(i) {
                // Get the original header text from the span with class "dt-column-title"
                let originalText = $(this).find('.dt-column-title').text().trim();
                
                // Clear the header cell and add a span for the title
                $(this).empty().append('<span style="display:block; font-weight:bold;">' + originalText + '</span>');
                
                // Create an input field with a placeholder and append it to the header cell
                let $input = $('<input type="text" class="col-search" placeholder="Search ' + originalText + '" style="width: 100%;">');
                $(this).append($input);

                // Attach event listener to perform column search
                $input.on('keyup change', function(e) {
                    self = this;
                    // draw(false) prevents page changes and doesfaster draw
                    if (api.column(i).search() !== this.value) {
                        api.column(i).search(this.value).draw(false).one('draw', function(){
                            // minor timeout to ensure DOM updates
                            setTimeout(function(){
                                self.focus();
                            },0)
                        })
                    }
                }); 
            });

            $('#softwareTable').show();
            api.columns.adjust(); // adjust columns if needed

        }
    });


/*////////////////////////////////////////////////////////////////
    Prevent clicking links in the table from Selecting the row //
*///////////////////////////////////////////////////////////////
    $('#softwareTable').on('click', 'a', function(e) {
        // Ensures this event listener doesn't trample 'Report Issue' event
        if ($("#reportIssueText").text() != 'Cancel')
        {
            e.stopPropagation();
        }
    }); 

/*///////////////////////////////////////////////////////////////
    Return softwareDetails modal to default state when closed //
*//////////////////////////////////////////////////////////////
    $('#softwareDetails-modal').on('hidden.bs.modal', function() {
        $('.collapse').each(function() {
            // Reopen all closed drawers except for Example Use
            if ($(this).attr('id') !== 'modalExampleUse' && !$(this).hasClass('show')) {
                $(this).addClass('show');
            } 
            // Reclose Example Use
            else if ($(this).attr('id') == 'modalExampleUse' && $(this).hasClass('show')) {
                $(this).removeClass('show');
            }
            history.pushState(null, '', '/');
        });
    });

/*/////////////////////
    Mouse Scrolling //
*////////////////////
    var $scrollBody = $('div.dt-scroll-body:last')  // If scrolling breaks, ensure that the table is the last dt-scroll-body
    var scrollSensitivity = 100; // Distance from edge in pixels.
    var scrollSpeed = 7; // Speed of the scroll step in pixels.
    var scrollInterval;
    var scrollDirection;

    // Event listener for mouse movement in the scroll body.
    $scrollBody.mousemove(function(e) 
    {
        var $this = $(this);
        var offset = $this.offset();
        var scrollWidth = $this[0].scrollWidth;
        var outerWidth = $this.outerWidth();
        var x = e.pageX - offset.left;
  
        // Right edge of the table.
        if (scrollWidth > outerWidth && x > outerWidth - scrollSensitivity) 
        {
            startScrolling(1); // Scroll right
        }
        // Left edge of the table.
        else if (x < scrollSensitivity) 
        {
            startScrolling(-1); // Scroll left
        } 
        else 
        {
            stopScrolling();
        }
    });
  
    $scrollBody.mouseleave(stopScrolling);

    checkScrollEdges();
    $scrollBody.on('scroll',checkScrollEdges);

    // Scrolling Behaviors
    function startScrolling(direction) 
    {
        if (scrollInterval) 
        {
            clearInterval(scrollInterval);
        }
        scrollDirection = direction;
        scrollInterval = setInterval(function() 
        {
        var currentScroll = $scrollBody.scrollLeft();
        $scrollBody.scrollLeft(currentScroll + scrollSpeed * scrollDirection);
        }, 10); // Interval in milliseconds
    }

    function checkScrollEdges()
    {
        let scrollLeft = $scrollBody.scrollLeft();
        var scrollWidth = $scrollBody[0].scrollWidth;
        var outerWidth = $scrollBody.outerWidth();

        if (scrollLeft+outerWidth >= (scrollWidth - 1))
        {
            $scrollBody.parent().addClass('no-right-shadow');
        }
        else
        {
            $scrollBody.parent().removeClass('no-right-shadow');
        }

        if (scrollLeft == 0)
        {
            $scrollBody.parent().addClass('no-left-shadow');
        }else
        {
            $scrollBody.parent().removeClass('no-left-shadow');
        }
    }

    function stopScrolling() 
    {
        clearInterval(scrollInterval);
    }
 
/*//////////////////////////////////////////////
    Disable Searching Through Hidden Columns //
*/////////////////////////////////////////////
    $.fn.dataTable.ext.search.push(
        function(settings, data, dataIndex) {
            var api = new $.fn.dataTable.Api(settings);
            var visibleColumns = api.columns(':visible').indexes().toArray();

            // Check if all visible columns for the row are empty
            var allEmpty = true;
            for (var i = 0; i < visibleColumns.length; i++) {
                var columnIndex = visibleColumns[i];
                if (data[columnIndex].trim() !== '') {
                    allEmpty = false;
                    break;
                }
            }

            return !allEmpty; // Show row if not all visible columns are empty
        }
    );

/*///////////////////////////////////////////////////
    Event Listener for Column Visibility Changes  //
*////////////////////////////////////////////////// 
    staticTable.on('column-visibility.dt', function(e, settings, column, state) {
        staticTable.draw();
    });

    // Check initial URL for parameter
    var initialSoftwareName = getURLParameter('software');
    if (initialSoftwareName) {
        showModalForSoftware(initialSoftwareName, staticTable);
    }

    // Modify the URL when a modal is opened
    staticTable.on('click', 'a[data-bs-target$="#softwareDetails-modal"]', function(e) {
        e.preventDefault();
        var softwareName = $(this).text(); // Assuming the software name is the text of the link
        history.pushState(null, '', '?software=' + encodeURIComponent(softwareName));
        showModalForSoftware(softwareName, staticTable);
    });

    staticTable.on('click','.example-use-btn', function(e){
        onExampleUseClick(e, staticTable);
    });

});

/*//////////////////////////////
    Clickable Links In Table //
*/////////////////////////////
export function makeLinkClickable(data) {
    var urlRegex = /(https?:\/\/[^\s<>]+)/g;  // Matches URLs starting with http/https and not containing whitespace or angle brackets
    if (data !== undefined) {
        return data.replace(urlRegex, function(url) {
            // Insert zero-width space after slashes or dots
            var spacedUrl = url.replace(/(\/|\.)+/g, '$&\u200B');
            return '<a href="' + url + '" target="_blank">' + spacedUrl + '</a>';
        });
    }
}

