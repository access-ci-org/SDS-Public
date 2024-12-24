import { setupFunctions, updateNavAndHeader } from "./navbarFooter.js";
import { showModalForSoftware, getURLParameter } from "./modals/softwareDetailsModal.js";
import { onExampleUseClick } from "./modals/exampleUseModal.js";

export var staticTable
export var COLUMN_MAP = JSON.parse(columnMap); // defined in software_search.html

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
        dom: 'PQ<"d-flex flex-column flex-md-row justify-content-between"\
                    <"d-flex flex-column flex-md-row"\
                        <"d-flex mb-3 mb-md-0"l>\
                        <"d-flex px-3"B>\
                    >\
                    <"d-flex justify-content-between align-items-center flex-grow-1"\
                        <"#toggleSearchTools">\
                    >\
                    <"d-flex justify-content-between align-items-center flex-grow-1"\
                        <"d-flex justify-content-start">\
                        <"d-flex scrollText-div">\
                    f>\
                >\
                rt\
                <"d-flex justify-content-between"ip>',
        searchPanes: {
            columns: [COLUMN_MAP['RPName'],
                    COLUMN_MAP["SoftwareType"],
                    COLUMN_MAP["ResearchArea"],
                    COLUMN_MAP["GeneralTags"]],
            threshold: 0.8,
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
                'colvisRestore',
                
            /*{
                extend: 'collection',
                text: 'Export',
                popoverTitle: 'Export Rows',
                autoClose: true,
                buttons: [
                    'copy', 
                    'excel',
                    'csv', 
                    {
                        extend: 'pdf',
                        orientation: 'landscape',
                        pageSize: "A2",
                        title: "Exported Software List",
                        download: 'open',
                        exportOptions: {
                            columns: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                            modifier: {
                                page: 'current'
                            },
                        },
                        customize: function(doc) {
                            doc.content[1].layout = "borders";
                        }
                    },
                    'print',
                ],
            },*/

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
            {   targets: [COLUMN_MAP['RPName']],
                searchPanes: {
                    name: 'RP Name',
                    className: 'noShadow',
                    options: [                   
                        {   label: 'Aces',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('aces');
                        }},                        
                        {   label: 'Anvil',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('anvil');
                        }},
                        {   label: 'Bridges-2',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('bridges-2');
                        }},
                        {   label: 'DARWIN',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('darwin');
                        }},                        
                        {   label: 'Delta',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('delta');
                        }},                        
                        {   label: 'Expanse',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('expanse');
                        }},                        
                        {   label: 'Faster',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('faster');
                        }},                        
                        {   label: 'Jetstream',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('jetstream');
                        }},                        
                        {   label: 'Kyric',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('kyric');
                        }},                        
                        {   label: 'Ookami',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('ookami');
                        }},                        
                        {   label: 'Stampede-3',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['RPName']].toLowerCase().includes('stampede3');
                        }}                        
                    ]
                }
            },
            
            {   targets: [COLUMN_MAP['SoftwareType']],           
                searchPanes: {
                    name: 'Software Type',
                    className: 'noShadow',
                    options: [
                        {   label: 'API',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('api');
                        }},
                        {   label: 'Application',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('application');
                        }},
                        {   label: 'Command Line',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('command');
                        }},
                        {   label: 'Compiler',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('compiler');
                        }},
                        {   label: 'Editor',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('editor');
                        }},
                        {   label: 'Framework',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('framework');
                        }},
                        {   label: 'Language',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('language');
                        }},
                        {   label: 'Library',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('library');
                        }},
                        {   label: 'Package',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('package');
                        }},
                        {   label: 'Parser',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('pars');
                        }},
                        {   label: 'Plugin',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('plug');
                        }},
                        {   label: 'Service',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('service');
                        }},
                        {   label: 'Software',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('software');
                        }},
                        {   label: 'Toolkit',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('toolkit');
                        }},
                        {   label: 'Utility',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['SoftwareType']].toLowerCase().includes('utility');
                        }},
            ]}},   
            {   targets: [COLUMN_MAP['ResearchArea']],               
                searchPanes: {
                    name: 'Research Area',
                    className: 'noShadow',
                    options: [
                        {   label: 'Artificial Intelligence',
                            value: function(rowData, rowIdx) {
                                return /\b(ai|artificial intelligence|machine learning|deep learning|natural language)\b/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }}, 
                        {   label: 'Astronomy/Cosmology',
                            value: function(rowData, rowIdx) {
                                return /(astro|cosmo)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }}, 
                        {   label: 'Biology',
                            value: function(rowData, rowIdx) {
                                return /(bio|genom|DNA|genet|sequenc|ngs|population|prote|sciences|transcriptomics)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }}, 
                        {   label: 'Chemistry',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['ResearchArea']].toLowerCase().includes('chemistry');
                        }}, 
                        {   label: 'Climate & Meteorology',
                            value: function(rowData, rowIdx) {
                                return /(climate|weather|meteor)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                        
                        {   label: 'Computer Science',
                            value: function(rowData, rowIdx) {
                                return /(comput|network|cyber|operating systems|program|software|visualization)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                        
                        {   label: 'Data Science/Management',
                            value: function(rowData, rowIdx) {
                                return /(data|info|infra)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},   
                        {   label: 'Ecology/Hydrology',
                            value: function(rowData, rowIdx) {
                                return /(ecology|environmental|hydro)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                      
                        {   label: 'Engineering',
                            value: function(rowData, rowIdx) {
                                return /(engineering|electrical|robotic)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},  
                        {   label: 'Health Sciences',
                            value: function(rowData, rowIdx) {
                                return /(health|epidemiolog|cancer|immun|medic)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                       
                        {   label: 'General Use',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['ResearchArea']].toLowerCase().includes('general');
                        }}, 
                        {   label: 'Genetics',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['ResearchArea']].toLowerCase().includes('genet');
                        }}, 
                        {   label: 'Mathematics',
                            value: function(rowData, rowIdx) {
                                return /(mathematics|statistics|geometry|graph|number|numer|optimization|quant)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},  
                        {   label: 'Physics',
                            value: function(rowData, rowIdx) {
                                return /(physics|dynamics|spectro)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                       
                        {   label: 'Neurology/Psychology',
                            value: function(rowData, rowIdx) {
                                return /(neuro|psych)/i.test(rowData[COLUMN_MAP['ResearchArea']]);
                        }},                        
            ]}},
            {   targets: [COLUMN_MAP['GeneralTags']],               
                searchPanes: {
                    name: 'General Tags',
                    className: 'noShadow',
                    show: true,
                    options: [
                        {   label: '2D',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('2d');
                        }},
                        {   label: '3D',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('3d');
                        }}, 
                        {   label: 'Alignment',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('alignment');
                        }},  
                        {   label: 'Artificial Intelligence',
                            value: function(rowData, rowIdx) {
                                return /\b(ai|artificial intelligence)\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},                         
                        {   label: 'Assembly',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('assembl');
                        }},
                        {   label: 'Astronomy',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('astro');
                        }},
                        {   label: 'Audio',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('audio');
                        }},
                        {   label: 'Bayesian',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('bayesian');
                        }},
                        {   label: 'Bioinformatics',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('bioinformatics');
                        }},
                        {   label: 'C',
                            value: function(rowData, rowIdx) {
                                return /\sc[,/\\\s]/.test(rowData[COLUMN_MAP['GeneralTags']].toLowerCase());
                        }},
                        {   label: 'C++',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('c++');
                        }},
                        {   label: 'Command Line',
                            value: function(rowData, rowIdx) {
                                return /\b(command[-\s]line)\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'Cross-Platform',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('cross-platform');
                        }},
                        {   label: 'CUDA',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('cuda');
                        }},
                        {   label: 'Deep Learning',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('deep learning');
                        }},
                        {   label: 'FastQ',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('fastq');
                        }},
                        {   label: 'Fortran',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('fortran');
                        }},
                        {   label: 'Genetics/Genomics',
                            value: function(rowData, rowIdx) {
                                return /(gene|genom)/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'GPU',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('gpu');
                        }},
                        {   label: 'Graph',
                            value: function(rowData, rowIdx) {
                                return /\b(graph )\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'Graphics',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('graphic');
                        }},
                        {   label: 'GUI',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('gui');
                        }},
                        {   label: 'High Performance Computing',
                            value: function(rowData, rowIdx) {
                                return /\b(hpc|high[-\s]performance computing)\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'HTML',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('html');
                        }},
                        {   label: 'Imaging',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('imag');
                        }}, 
                        {   label: 'Java',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('java');
                        }}, 
                        {   label: 'JSON',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('json');
                        }}, 
                        {   label: 'Library',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('library');
                        }}, 
                        {   label: 'Linux',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('linux');
                        }}, 
                        {   label: 'Machine Learning',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('machine learning');
                        }},
                        {   label: 'Neural Network',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('neural network');
                        }},
                        {   label: 'Open Source',
                            value: function(rowData, rowIdx) {
                                return /open[\s-]source/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'OpenGL',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('opengl');
                        }},
                        {   label: 'Optimization',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('optimization');
                        }},
                        {   label: 'Parser',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('parser');
                        }},
                        {   label: 'Phylogenics',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('phylogenics');
                        }},
                        {   label: 'Python',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('python');
                        }},
                        {   label: 'Pytorch',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('pytorch');
                        }},
                        {   label: 'R',
                            value: function(rowData, rowIdx) {
                                return /\b(R )\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'Sequencing',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('sequencing');
                        }},
                        {   label: 'Software',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('software');
                        }},
                        {   label: 'Unicode',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('unicode');
                        }},
                        {   label: 'User Interface',
                            value: function(rowData, rowIdx) {
                                return /\b(ui|user[\s-]interface)\b/i.test(rowData[COLUMN_MAP['GeneralTags']]);
                        }},
                        {   label: 'Visualization',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('visualization');
                        }}, 
                        {   label: 'Web',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('web');
                        }}, 
                        {   label: 'XML',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('xml');
                        }}, 
                        {   label: 'YAML',
                            value: function(rowData, rowIdx) {
                                return rowData[COLUMN_MAP['GeneralTags']].toLowerCase().includes('yaml');
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
                targets:[COLUMN_MAP["ExampleUse"]],
                render: function(data, type, row) {
                    return '<button class="btn btn-info example-use-btn" type="button">Use Example</button>';
            }},
            {   // Columns with clickable URLs
                targets: [COLUMN_MAP["SoftwareDescription"],
                        COLUMN_MAP["SoftwareDocumentation"],
                        COLUMN_MAP["SoftwaresWebPage"],
                        COLUMN_MAP["ExampleSoftwareUse"],
                        COLUMN_MAP["RPSoftwareDocumentation"]], 
                render: function(data, type, row) {
                    if (type === 'display' && data) {
                        return makeLinkClickable(data);
                    } return data;
            }}, 
            { width: '65px', targets: [COLUMN_MAP["RPName"]], className: 'dt-center' },
            { width: '100px', targets: [COLUMN_MAP["ExampleUse"]], className: 'dt-center'},
            { width: '100px', targets: [COLUMN_MAP["ResearchArea"]], className: 'dt-center'},
            { width: '110px', targets: [COLUMN_MAP["SoftwareType"],
                                        COLUMN_MAP["ResearchField"]], className: 'dt-center'},
            { width: '115px', targets: [COLUMN_MAP["SoftwareClass"]], className: 'dt-center'},
            { width: '120px', targets: [COLUMN_MAP["VersionInfo"]], className: 'dt-center'},
            { width: '110px', targets: [COLUMN_MAP["ResearchDiscipline"]], className: 'dt-center'},
            { width: '180px', targets: [COLUMN_MAP["GeneralTags"]], className: 'dt-center'},
            { width: '300px', targets: [COLUMN_MAP["SoftwareDocumentation"],
                                        COLUMN_MAP["SoftwaresWebPage"],
                                        COLUMN_MAP["ExampleSoftwareUse"],
                                        COLUMN_MAP["RPSoftwareDocumentation"]], className: 'dt-center'},
            { width: '400px', targets: [COLUMN_MAP["AIDescription"],COLUMN_MAP["CoreFeatures"]], className: 'dt-center'}, // AI Description, Core Features
            { width: '500px', targets: [COLUMN_MAP["SoftwareDescription"]], className: 'dt-center'},
        ],
        initComplete: function() {
            $('#toggleSearchTools').html(`<button id="toggleFiltersButton" class="dtsp-toggleButton">Show Search Tools</button>`)
            $('.scrollText-div').html("Hover your mouse to the edge of the table to scroll");
            $('#softwareTable').show(); // show the table (it is initially hidden to save load time)
            var table = this.api();
            table.columns.adjust().draw();
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
    staticTable.on('click', 'a[data-target$="#softwareDetails-modal"]', function(e) {
        e.preventDefault();
        var softwareName = $(this).text(); // Assuming the software name is the text of the link
        history.pushState(null, '', '?software=' + encodeURIComponent(softwareName));
        showModalForSoftware(softwareName, staticTable);
    });

    staticTable.on('click','.example-use-btn', function(e){
        onExampleUseClick(e);
    });
});

/*//////////////////////////////
    Clickable Links In Table //
*/////////////////////////////
export function makeLinkClickable(data) 
{
    var urlRegex = /(https?:\/\/[^\s]+)/g;
    return data.replaceAll(urlRegex, function(url) 
    {
        // Insert zero-width space after slashes or dots, as an example
        var spacedUrl = url.replace(/(\/|\.)+/g, '$&\u200B');
        return '<a href="' + url + '" target="_blank">' + spacedUrl + '</a>';
    });
}

/*///////////////////////////////////////////////////////////////
    Creates the Button to Hide/Show the Search Panes //
*//////////////////////////////////////////////////////////////

$(document).ready(function() {
    // Initially hide the search panes
    $('.dtsp-panesContainer , .dtsb-searchBuilder').addClass('d-none');

    $('#toggleFiltersButton').on('click', function() {
        // Toggle visibility of the elements
        $('.dtsp-panesContainer , .dtsb-searchBuilder').toggleClass('d-none');

        // Toggle button text between "Show Filters" and "Hide Filters"
        const buttonText = $(this).text() === 'Show Search Tools' ? 'Hide Search Tools' : 'Show Search Tools';
        $(this).text(buttonText);
    });
});