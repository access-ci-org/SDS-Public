import {header, siteMenus, footer, footerMenus, universalMenus} from "https://esm.sh/@access-ci/ui@0.2.0"

const siteItems = [{
        name: "ACCESS Resource Advisor",
        href: "https://access-ara.ccs.uky.edu:8080/"
    }
]

export var staticTable

$(document).ready(function()
{
/*//////////////////////////////////////
    ACCESS Website Predfined Content //
*/////////////////////////////////////
    universalMenus({
        loginUrl: "/login",
        logoutUrl: "/logout",
        siteName: "Allocations",
        target: document.getElementById("universal-menus"),
    });
    header({
        siteName: "Support",
        target: document.getElementById("header")
    });
    siteMenus({
        items: siteItems,
        siteName: "Allocations",
        target: document.getElementById("site-menus"),
      });

    footerMenus({
        items: siteItems,
        target: document.getElementById("footer-menus"),
    });
    footer({ target: document.getElementById("footer") });

    const NavShadowHost = document.getElementById('universal-menus');
    const shadowRoot = NavShadowHost.shadowRoot;
    const loginButton = shadowRoot.querySelector('li:last-child button');
    loginButton.remove();

    $("#app_content").removeClass()
    $("#app_content").addClass('col')


/*/////////////////////////////////////////////////////////////////////////////////////////////////////////
    STATIC TABLE                                                                                        //
    Enabled: Buttons (Column Visibility), FixedColumn, FixedHeader, SearchBuilder, SearchPanes, Select //
*///////////////////////////////////////////////////////////////////////////////////////////////////////
    staticTable = $('#softwareTable').DataTable({
        select: {           // Allows for selecting rows in tables/searchPanes
            enabled: true,
            style: 'multi', // Select multiple rows, deselect by clicking again
        },       
        fixedColumns: true, // Makes first column 'fixed' to the left side of the table when scrolling
        fixedHeader: true,  // Makes column headers 'fixed' to the top of the table when scrolling
        "sScrollX": "100%", // Enables horizontal scrolling
        autoWidth: true,    // Column width is determined dynamically by content within the cells
        pageLength: 25,     // Rows displayed per page
        pagingType: 'full_numbers',     // 'First', 'Previous', 'Next', 'Last', with page numbers
        lengthMenu: [                   // User-selectable menu for pageLength
            [10, 25, 50, 250, 500, -1],
            [10, 25, 50, 250, 500, 'All']
        ],
        // DOM: 'P' = searchPanes, 'Q' = searchBuilder. The rest is various layout and formatting options.
        // For example: 'p' affects the paging style at the bottom of the table.
        dom: 'PQ<"d-flex flex-column flex-md-row justify-content-between"<"d-flex flex-column flex-md-row"<"d-flex mb-3 mb-md-0"l><"d-flex px-3"B>><"d-flex justify-content-between align-items-center flex-grow-1"<"d-flex justify-content-start"><"d-flex scrollText-div">f>>rt<"d-flex justify-content-between"ip>',
        initComplete: function()
        {
            $('.scrollText-div').html("Hover your mouse to the edge of the table to scroll")          
        },
        searchPanes: {
            columns: [1,2,5,9],
            //threshold: 0.8,
            initCollapsed: true,
            cascadePanes: false,    // Reflects one change in the searchPanes filters across all Panes.
                                    // Unfortunately, can't use this until we optimize the table's performance.
            dtOpts: {
                select: {
                    style: 'multi'  // Allows for selecting multiple rows.
                }, 
            },
            combiner: 'or'          // in searchPanes, selecting multiple rows 'OR's them together.
                                    // Default behavior is 'AND'
        },
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
                'colvisRestore' 
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
        columnDefs: [
            {   targets: [1],
                searchPanes: { 
                    name: 'RP Name',
                    className: 'noShadow',
                    options: [                   
                        {   label: 'Aces',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('aces');
                        }},                        
                        {   label: 'Anvil',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('anvil');
                        }},
                        {   label: 'Bridges-2',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('bridges-2');
                        }},
                        {   label: 'DARWIN',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('darwin');
                        }},                        
                        {   label: 'Delta',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('delta');
                        }},                        
                        {   label: 'Expanse',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('expanse');
                        }},                        
                        {   label: 'Faster',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('faster');
                        }},                        
                        {   label: 'Jetstream',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('jetstream');
                        }},                        
                        {   label: 'Kyric',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('kyric');
                        }},                        
                        {   label: 'Ookami',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('ookami');
                        }},                        
                        {   label: 'Stampede-3',
                            value: function(rowData, rowIdx) {
                                return rowData[1].toLowerCase().includes('stampede3');
                        }}                        
            ]}},             
            {   targets: [2],           
                searchPanes: {
                    name: 'Software Type',
                    className: 'noShadow',
                    options: [
                        {   label: 'API',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('api');
                        }},
                        {   label: 'Application',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('application');
                        }},
                        {   label: 'Command Line',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('command');
                        }},
                        {   label: 'Compiler',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('compiler');
                        }},
                        {   label: 'Editor',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('editor');
                        }},
                        {   label: 'Framework',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('framework');
                        }},
                        {   label: 'Language',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('language');
                        }},
                        {   label: 'Library',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('library');
                        }},
                        {   label: 'Package',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('package');
                        }},
                        {   label: 'Parser',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('pars');
                        }},
                        {   label: 'Plugin',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('plug');
                        }},
                        {   label: 'Service',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('service');
                        }},
                        {   label: 'Software',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('software');
                        }},
                        {   label: 'Toolkit',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('toolkit');
                        }},
                        {   label: 'Utility',
                            value: function(rowData, rowIdx) {
                                return rowData[2].toLowerCase().includes('utility');
                        }},
            ]}},   
            {   targets: [5],               
                searchPanes: {
                    name: 'Research Area',
                    className: 'noShadow',
                    options: [
                        {   label: 'Artificial Intelligence',
                            value: function(rowData, rowIdx) {
                                return /\b(ai|artificial intelligence|machine learning|deep learning|natural language)\b/i.test(rowData[5]);
                        }}, 
                        {   label: 'Astronomy/Cosmology',
                            value: function(rowData, rowIdx) {
                                return /(astro|cosmo)/i.test(rowData[5]);
                        }}, 
                        {   label: 'Biology',
                            value: function(rowData, rowIdx) {
                                return /(bio|genom|DNA|genet|sequenc|ngs|population|prote|sciences|transcriptomics)/i.test(rowData[5]);
                        }}, 
                        {   label: 'Chemistry',
                            value: function(rowData, rowIdx) {
                                return rowData[5].toLowerCase().includes('chemistry');
                        }}, 
                        {   label: 'Climate & Meteorology',
                            value: function(rowData, rowIdx) {
                                return /(climate|weather|meteor)/i.test(rowData[5]);
                        }},                        
                        {   label: 'Computer Science',
                            value: function(rowData, rowIdx) {
                                return /(comput|network|cyber|operating systems|program|software|visualization)/i.test(rowData[5]);
                        }},                        
                        {   label: 'Data Science/Management',
                            value: function(rowData, rowIdx) {
                                return /(data|info|infra)/i.test(rowData[5]);
                        }},   
                        {   label: 'Ecology/Hydrology',
                            value: function(rowData, rowIdx) {
                                return /(ecology|environmental|hydro)/i.test(rowData[5]);
                        }},                      
                        {   label: 'Engineering',
                            value: function(rowData, rowIdx) {
                                return /(engineering|electrical|robotic)/i.test(rowData[5]);
                        }},  
                        {   label: 'Health Sciences',
                            value: function(rowData, rowIdx) {
                                return /(health|epidemiolog|cancer|immun|medic)/i.test(rowData[5]);
                        }},                       
                        {   label: 'General Use',
                            value: function(rowData, rowIdx) {
                                return rowData[5].toLowerCase().includes('general');
                        }}, 
                        {   label: 'Genetics',
                            value: function(rowData, rowIdx) {
                                return rowData[5].toLowerCase().includes('genet');
                        }}, 
                        {   label: 'Mathematics',
                            value: function(rowData, rowIdx) {
                                return /(mathematics|statistics|geometry|graph|number|numer|optimization|quant)/i.test(rowData[5]);
                        }},  
                        {   label: 'Physics',
                            value: function(rowData, rowIdx) {
                                return /(physics|dynamics|spectro)/i.test(rowData[5]);
                        }},                       
                        {   label: 'Neurology/Psychology',
                            value: function(rowData, rowIdx) {
                                return /(neuro|psych)/i.test(rowData[5]);
                        }},                        
            ]}},
            {   targets: [9],               
                searchPanes: {
                    name: 'General Tags',
                    className: 'noShadow',
                    show: true,
                    options: [
                        {   label: '2D',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('2d');
                        }},
                        {   label: '3D',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('3d');
                        }}, 
                        {   label: 'Alignment',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('alignment');
                        }},  
                        {   label: 'Artificial Intelligence',
                            value: function(rowData, rowIdx) {
                                return /\b(ai|artificial intelligence)\b/i.test(rowData[9]);
                        }},                         
                        {   label: 'Assembly',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('assembl');
                        }},
                        {   label: 'Astronomy',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('astro');
                        }},
                        {   label: 'Audio',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('audio');
                        }},
                        {   label: 'Bayesian',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('bayesian');
                        }},
                        {   label: 'Bioinformatics',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('bioinformatics');
                        }},
                        {   label: 'C',
                            value: function(rowData, rowIdx) {
                                return /\sc[,/\\\s]/.test(rowData[9].toLowerCase());
                        }},
                        {   label: 'C++',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('c++');
                        }},
                        {   label: 'Command Line',
                            value: function(rowData, rowIdx) {
                                return /\b(command[-\s]line)\b/i.test(rowData[9]);
                        }},
                        {   label: 'Cross-Platform',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('cross-platform');
                        }},
                        {   label: 'CUDA',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('cuda');
                        }},
                        {   label: 'Deep Learning',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('deep learning');
                        }},
                        {   label: 'FastQ',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('fastq');
                        }},
                        {   label: 'Fortran',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('fortran');
                        }},
                        {   label: 'Genetics/Genomics',
                            value: function(rowData, rowIdx) {
                                return /(gene|genom)/i.test(rowData[9]);
                        }},
                        {   label: 'GPU',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('gpu');
                        }},
                        {   label: 'Graph',
                            value: function(rowData, rowIdx) {
                                return /\b(graph )\b/i.test(rowData[9]);
                        }},
                        {   label: 'Graphics',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('graphic');
                        }},
                        {   label: 'GUI',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('gui');
                        }},
                        {   label: 'High Performance Computing',
                            value: function(rowData, rowIdx) {
                                return /\b(hpc|high[-\s]performance computing)\b/i.test(rowData[9]);
                        }},
                        {   label: 'HTML',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('html');
                        }},
                        {   label: 'Imaging',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('imag');
                        }}, 
                        {   label: 'Java',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('java');
                        }}, 
                        {   label: 'JSON',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('json');
                        }}, 
                        {   label: 'Library',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('library');
                        }}, 
                        {   label: 'Linux',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('linux');
                        }}, 
                        {   label: 'Machine Learning',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('machine learning');
                        }},
                        {   label: 'Neural Network',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('neural network');
                        }},
                        {   label: 'Open Source',
                            value: function(rowData, rowIdx) {
                                return /open[\s-]source/i.test(rowData[9]);
                        }},
                        {   label: 'OpenGL',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('opengl');
                        }},
                        {   label: 'Optimization',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('optimization');
                        }},
                        {   label: 'Parser',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('parser');
                        }},
                        {   label: 'Phylogenics',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('phylogenics');
                        }},
                        {   label: 'Python',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('python');
                        }},
                        {   label: 'Pytorch',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('pytorch');
                        }},
                        {   label: 'R',
                            value: function(rowData, rowIdx) {
                                return /\b(R )\b/i.test(rowData[9]);
                        }},
                        {   label: 'Sequencing',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('sequencing');
                        }},
                        {   label: 'Software',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('software');
                        }},
                        {   label: 'Unicode',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('unicode');
                        }},
                        {   label: 'User Interface',
                            value: function(rowData, rowIdx) {
                                return /\b(ui|user[\s-]interface)\b/i.test(rowData[9]);
                        }},
                        {   label: 'Visualization',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('visualization');
                        }}, 
                        {   label: 'Web',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('web');
                        }}, 
                        {   label: 'XML',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('xml');
                        }}, 
                        {   label: 'YAML',
                            value: function(rowData, rowIdx) {
                                return rowData[9].toLowerCase().includes('yaml');
                        }},          
            ]}},
            {   // Disables all other columns not explicitly shown from displaying as Panes
                targets: "_all",
                searchPanes: {
                    show: false
            }}, 
            {   // Enable searchBuilder on all columns 
                targets: "_all",
                searchBuilder: { 
                        defaultCondition: 'contains'
            }},  
            {   // Software Details Modal  
                target: [0],             
                render: function(data, type, row) {
                    if (type === 'display') {
                            return '<a data-toggle="modal" data-target="#softwareDetails-modal" href="#">' + data + '</a>'
                        } return data
            }},   
            {   // Example Use Modal
                targets:[16],
                render: function(data, type, row) {
                    return '<button class="btn btn-info example-use-btn" type="button">Use Example</button>';
            }},
            {   // Columns with clickable URLs
                targets: [7,10,11,12,13], 
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        return makeLinkClickable(data);
                    } return data;
            }}, 
            { width: '65px', targets: [1], className: 'dt-center' },    // RP Names
            { width: '100px', targets: [16], className: 'dt-center'},   // Example Use Button
            { width: '100px', targets: [5], className: 'dt-center'},    // Research Area
            { width: '110px', targets: [2,4], className: 'dt-center'},  // Software Type, Research Field
            { width: '115px', targets: [3], className: 'dt-center'},    // Software Class
            { width: '120px', targets: [14], className: 'dt-center'},   // Version Info
            { width: '110px', targets: [6], className: 'dt-center'},    // Research Discipline
            { width: '180px', targets: [9], className: 'dt-center'},    // General Tags
            { width: '300px', targets: [10,11,12,13], className: 'dt-center'}, // Software Links
            { width: '400px', targets: [8,15], className: 'dt-center'}, // Core Features, AI Description
            { width: '500px', targets: [7], className: 'dt-center'},    // Software Description
        ],
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

/*/////////////////////////////////////////////////////////////////////
    Initialize a Showdown converter with the Highlight.js extension //
*////////////////////////////////////////////////////////////////////
    var converter = new showdown.Converter({
        extensions: [highlightExtension]
    });

/*//////////////////////////////////////////////////////
    Event Listener for Software 'Example Use' Modal  //
*/////////////////////////////////////////////////////    
    staticTable.on('click','.example-use-btn', function(e){
        e.stopPropagation()
        let rowData = staticTable.row(e.target.closest('tr')).data();
        var softwareName = rowData[0];
        var encodedSoftwareName = encodeURIComponent(softwareName);
        $.ajax({
            url: "/example_use/"+encodedSoftwareName,
            type:"GET",
            success: function(response){

                var useHtml = converter.makeHtml(response.use)
                $("#useCase-modal-title").text('Use Case for ' + softwareName)
                $('#useCaseBody').html(useHtml);

                document.querySelectorAll('#useCaseBody pre Code').forEach((block)=>{
                    hljs.highlightElement(block)
                })

                $('#useCase-modal').modal('show');
            },
            error: function(xhr, status, error){
                console.error("Error fetching example use: ", error);
        }})
    })

/*///////////////////////////////////////////////
    Event Listener for Software Details Modal //
*//////////////////////////////////////////////
    staticTable.on('click', 'a[data-target$="#softwareDetails-modal"]', function(e){
        // Prevent webpage scrolling to top behind modal
        e.preventDefault();

        // Grab the row of the clicked software 
        const row = staticTable.row(e.target.closest('tr'));

        // Stage the row info to be injected into the modal
        const rowData = row.data();
        
        // Prevents rare situation of malforned Description spawning multiple dividers
        if (!rowData[6].includes('<hr>'))
        {
            rowData[6] = rowData[6].replace('Description Source', '<hr>Description Source');
        }

        rowData[7] = rowData[7].replaceAll('<br>', '<hr>');
        // Visually separate multiple entries with line divider
        rowData[12] = rowData[12].replaceAll('<br>', '<hr>');
        rowData[13] = rowData[13].replaceAll('<br>', '<hr>');
        rowData[14] = rowData[14].replaceAll('<br>', '<hr>');

        // Populate the softwareDetails modal
        // Curated
        $('#softwareDetails-modal-title').html("Software Details: " + rowData[0]);
        $('#softwareDetailsName').text(rowData[0]);
        $('#softwareDetailsRPs').text(rowData[1]);
        $('#softwareDetailsType').html(rowData[2]);
        $('#softwareDetailsClass').html(rowData[3]);
        $('#softwareDetailsField').html(rowData[4]);
        $('#softwareDetailsArea').html(rowData[5]);
        $('#softwareDetailsDiscipline').html(rowData[6]);
        $('#softwareDetailsDescription').html(makeLinkClickable(rowData[7]));
        $('#softwareDetailsWebpage').html(makeLinkClickable(rowData[10]));
        $('#softwareDetailsDocumentation').html(makeLinkClickable(rowData[11]));
        $('#softwareDetailsExamples').html(makeLinkClickable(rowData[12]));
        $('#softwareDetailsRPDocs').html(makeLinkClickable(rowData[13]));
        $('#softwareDetailsVersions').html(rowData[14]);

        // AI
        $('#softwareDetailsCoreFeat').html(rowData[8]);
        $('#softwareDetailsTags').text(rowData[9]);
        $('#softwareDetailsAIDesc').text(rowData[15]);

        // Inject Example Use into Modal
        var softwareName = rowData[0];
        var encodedSoftwareName = encodeURIComponent(softwareName);
        $.ajax({
            url: "/example_use/"+encodedSoftwareName,
            type:"GET",
            success: function(response){

                var useHtml = converter.makeHtml(response.use)
                $("#modalExampleTitle").text('Example Use for ' + softwareName)
                $('#modalExampleUse').html(useHtml);

                document.querySelectorAll('#modalExampleUse pre Code').forEach((block)=>{
                    hljs.highlightElement(block)
                })
            },
            error: function(xhr, status, error){
                console.error("Error fetching example use: ", error);
            }
        })
        // Show modal
        $('#softwareDetails-modal').modal('show');
    })   
});

/*//////////////////////////////
    Clickable Links In Table //
*/////////////////////////////
function makeLinkClickable(data) 
{
    var urlRegex = /(https?:\/\/[^\s]+)/g;
    return data.replaceAll(urlRegex, function(url) 
    {
        // Insert zero-width space after slashes or dots, as an example
        var spacedUrl = url.replace(/(\/|\.)+/g, '$&\u200B');
        return '<a href="' + url + '" target="_blank">' + spacedUrl + '</a>';
    });
}

/*//////////////////////////////////////////
    Highlight.js for 'Example Use' modal //
*/////////////////////////////////////////
// Define the Highlight.js extension for Showdown
function highlightExtension() {
    return [{
        type: 'output',
        filter: function (text, converter, options) {
            var left = '<pre><code\\b[^>]*>',
                right = '</code></pre>',
                flags = 'g',
                replacement = function (wholeMatch, match, left, right) {
                    match = match.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
                    return left + hljs.highlightAuto(match).value + right;
                };
            return showdown.helper.replaceRecursiveRegExp(text, replacement, left, right, flags);
        }
    }];
}


