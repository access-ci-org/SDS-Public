import { showModalForSoftware, getURLParameter } from "./modals/softwareDetailsModal.js";
import { onExampleUseClick } from "./modals/exampleUseModal.js";
import { onViewContainerClick } from "./modals/containerModal.js";

export var staticTable
export var column_names = JSON.parse(col_names) // defined in software_search.html

$(document).ready(function()
{
    const columnWidths = {
        'software_name': '120px',
        'resource_name': '125px',
        'container': '90px',
        'software_description': '550px',
        'ai_description': '400px',
        'ai_software_type': '110px',
        'ai_software_class': '115px',
        'ai_research_field': '110px',
        'ai_research_area': '100px',
        'ai_research_discipline': '110px',
        'ai_core_features': '400px',
        'ai_general_tags': '180px',
        'software_version': '160px',
        'software_web_page': '300px',
        'software_documentation': '300px',
        'software_use_link': '300px',
        'ai_example_use': '150px'
    };

    /*/////////////////////////////////////////////////////////////////////////////////////////////////////////
        STATIC TABLE                                                                                        //
        Enabled: Buttons (Column Visibility), FixedColumn, FixedHeader, SearchBuilder, SearchPanes, Select //
    *///////////////////////////////////////////////////////////////////////////////////////////////////////
    var staticTable = $('#softwareTable').DataTable({
        select: {           // Allows for selecting rows in tables/searchPanes
            enabled: true,
            style: 'multi', // Select multiple rows, deselect by clicking again
        },
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
        // DOM: 'P' = searchPanes, 'Q' = searchBuilder. The rest is various layout and formatting options.
        // For example: 'p' affects the paging style at the bottom of the table.
        dom: 'Q<"d-flex flex-column flex-md-row justify-content-between"\
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
            searchBuilder: {
                title: {    // Change text for searchBuilder Title
                    0: 'Advanced Search',       // Zero filters selected
                    _: 'Advanced Search (%d)'   // Any other number (%d is a placeholder for the number)
                }
            }
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
        searchBuilder: {
            conditions: {
                string: {
                    '=': null,
                    'null':null,
                    '!null':null,
                    '!=':null,
                    'starts':null,
                    '!starts':null,
                    'ends':null,
                    '!ends':null,
                    '!contains':null,
        }}},
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

                // const displayName = $(this).text().trim();
                // const internalKey = reverseColumnMap[displayName];
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
                         'software_web_page', 'software_use_link'].includes(internalKey)) {
                    column.render = function(data, type, row) {
                        if (type === 'display' && data) {
                            return makeLinkClickable(data);
                        }
                        return data;
                    };
                } else if (internalKey === 'container'){
                    column.render = function(data, type, row){
                        if (type== 'display' && data !== 'N/A') {
                            return "<a class='viewContainer' href='#' onClick='return false;'> view containers</a>";
                        }
                        return data;
                    }
                }
                cols.push(column);
            });
            return cols;
        }(),
        columnDefs: [
           {
                targets: "_all",
                searchBuilder: {
                    defaultCondition: 'contains'
                },
            },
        ],
        initComplete: function() {
            $('.scrollText-div').html("Hover your mouse to the edge of the table to scroll");
            $('#softwareTable').show();
            var table = this.api();
            table.columns.adjust().draw()
        },
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

    staticTable.on('click','.viewContainer', function(e){
        onViewContainerClick(e, staticTable);
    });

    $("#container-modal").on("hide.bs.modal", ()=>{
        $("#container-accordion").html("")
    })

});

/*//////////////////////////////
    Clickable Links In Table //
*/////////////////////////////
export function makeLinkClickable(data) 
{
    var urlRegex = /(https?:\/\/[^\s]+)/g;
    if (data !== undefined){
        return data.replaceAll(urlRegex, function(url)
        {
            // Insert zero-width space after slashes or dots, as an example
            var spacedUrl = url.replace(/(\/|\.)+/g, '$&\u200B');
            return '<a href="' + url + '" target="_blank">' + spacedUrl + '</a>';
        });
    }
}
