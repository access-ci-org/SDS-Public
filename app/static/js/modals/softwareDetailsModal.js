
/*////////////////////////////////////////////////////////////////
    Function for URL identification for quick access to modals //
*///////////////////////////////////////////////////////////////
export function getURLParameter(name) {
    return decodeURIComponent((new RegExp('[?|&]' + name + '=' + '([^&;]+?)(&|#|;|$)').exec(location.search) || [,""])[1].replace(/\+/g, '%20')) || null;
}

/*///////////////////////////////////////////////
    Event Listener for Software Details Modal //
*//////////////////////////////////////////////

async function  getSoftwareModalData(softwareName) {
    // Trigger the modal logic
    var encodedSoftwareName = encodeURIComponent(softwareName);

    return new Promise ((resolve, reject) => {
        $.ajax({
        url: "/software_info/" + encodedSoftwareName,
        type: "GET",
        success: function(response) {
            if (response){
                resolve(JSON.parse(response)[0])
            } else {
                reject("No data found for "+ softwareName)
            }
        },
        error: function(xhr, status, error) {
            console.error("Error fetching software info: ", error);
            reject(error);
        }
        })
    })
}

async function getSoftwareExampleUse(softwareName) {
    var encodedSoftwareName = encodeURIComponent(softwareName);
    return new Promise ((resolve, reject) => {
        $.ajax({
            url: "/example_use/" + encodedSoftwareName,
            type: "GET",
            success: function(response) {
                if (response) {
                    var useHtml = response.use;
                    resolve(useHtml)
                } else {
                    reject("No example use found for " + softwareName)
                }
            },
            error: function(xhr, status, error) {
                console.error("Error fetching example use: ", error);
                reject(error)
            }
        });
    });
}

const RESOURCE_LINKS = {
    "aces": "https://allocations.access-ci.org/resources/aces.tamu.access-ci.org",
    "anvil": "https://allocations.access-ci.org/resources/anvil.purdue.access-ci.org",
    "bridges-2": "https://allocations.access-ci.org/resources/bridges2.psc.access-ci.org",
    "delta": "https://allocations.access-ci.org/resources/delta.ncsa.access-ci.org",
    "deltaai": "https://allocations.access-ci.org/resources/deltaai.ncsa.access-ci.org",
    "derecho": "https://allocations.access-ci.org/resources/derecho.ncar.access-ci.org",
    "expanse": "https://allocations.access-ci.org/resources/expanse.sdsc.access-ci.org",
    "faster": "https://allocations.access-ci.org/resources/faster.tamu.access-ci.org",
    "granite": "https://allocations.access-ci.org/resources/granite.ncsa.access-ci.org",
    "jetstream2": "https://allocations.access-ci.org/resources/jetstream2.indiana.access-ci.org",
    "kyric": "https://allocations.access-ci.org/resources/kyric.uky.access-ci.org",
    "launch": "https://allocations.access-ci.org/resources/launch.tamu.access-ci.org",
    "neocortex": "https://allocations.access-ci.org/resources/neocortex.psc.access-ci.org",
    "ookami": "https://allocations.access-ci.org/resources/ookami.sbu.access-ci.org",
    "repacss": "https://allocations.access-ci.org/resources/repacss.ttu.access-ci.org",
    "stampede3": "https://allocations.access-ci.org/resources/stampede3.tacc.access-ci.org",
    "voyager": "https://allocations.access-ci.org/resources/voyager.sdsc.access-ci.org",
}

function formatSoftwareInfo(softwareInfo) {
    let softwareData = {}
    /* Example of what the return looks like
    softwareData["installedOn"] = {
        resource1:
            {resourceLink: allocations_link,
                resourceDocumentation: documentation link,
                resourceVersion: [versions]},
        resource2:
            {resourceLink: allocations_link,
                resourceDocumentation: documentation link,
                resourceVersion: [versions]}
        }
    softwareData["description"] = description
    softwareData["coreFeatures"] = core_features
    softwareData["relatedLinks"] = {
        websiteLink: {
            Website_title: link
        },
        documentationLink: {
            Website_title: link
        }
        tutorialLink: {
            Website_title: link,
            WebsiteTitle: link
        }
        }

    software["Similar Software"] = {
        tags: [tag1, tag2, tag3],
        researchDiscipline: [rf1, rf2, rf3],
        softwareType: [st1, st2, st3]
        }
    */
    const resources = softwareInfo["Installed on" || ""].split("\n").filter(x => x.trim())
    const versions = softwareInfo["Versions" || ""].split("\n").filter(x => x.trim())
    const resourcePageLink = "https://allocations.access-ci.org/resources"
    const resourceDocumentation = softwareInfo["RP Software Documentation" || ""].split("\n").filter(x => x.trim())
    const tutorialLinks = softwareInfo["Example Software Use" || ""].split("\n").filter(x => x.trim())
    const researchDiscipline = softwareInfo["AI Research Discipline"].split(",")
    const softwareType = softwareInfo["AI Software Type"].split(",").filter(x => x.trim())

    softwareData["installedOn"] = Object.fromEntries(
        resources.map(resource => [
            resource,
            {
                resourceLink: RESOURCE_LINKS[resource.toLocaleLowerCase()] || resourcePageLink,
                resourceDocumentation: resourceDocumentation
                    .filter(version => version.startsWith(resource.toLowerCase() + ': '))
                    .map(version => version.slice((resource.toLowerCase() + ': ').length).trim().split(',').map(item => item.trim()))
                    .flat()[0], // there should only be one documentatino link so get the first item
                resourceVersion: versions
                    .filter(version => version.startsWith(resource + ':'))
                    .map(version => version.slice((resource + ':').length).trim().split(',').map(item => item.trim()))
                    .flat()
            }
        ])
    );
    softwareData["description"] = softwareInfo["AI Description"] || softwareInfo["Description"] || ""
    softwareData["coreFeatures"] = softwareInfo["AI Core Features"] || ""
    softwareData["relatedLinks"] = {
        "websiteLink" : {
            "Software Page": softwareInfo["Software's Web Page"] || ""
        },
        "documentationLink": {
            "Software Documentation": softwareInfo["Software Documentation"] || ""
        },
        "tutorialLink": Object.fromEntries(
            tutorialLinks.map((link, index) => [link, link])
        ),
    }

    softwareData["similarSoftware"] = {
        "tags": softwareInfo["AI Tags" || ""].split(",").filter(x => x.trim()),
        "researchDiscipline": researchDiscipline,
        "softwareType": softwareType
    }

    return softwareData
}

function isEmpty(value){
    if (value === null) return true;

    if (typeof value === 'string') return value.trim() === '';

    if (Array.isArray(value)) return value.length === 0;

    if (typeof value === 'object') {
        const keys = Object.keys(value);
        if (keys.length === 0) return true;

        return keys.every(key => isEmpty(value[key]));
    }

    return false;
}

const SIMILAR_SOFTWARE_CONFIGS = {
    tags: { icon: 'tag', className: 'tag', title: 'TAGS' },
    researchDiscipline: { icon: 'journal-text', className: 'research-discipline', title: 'RESEARCH DISCIPLINE' },
    softwareType: { icon: 'terminal', className: 'software-type', title: 'SOFTWARE TYPE' }
};

const LINK_CONFIGS = {
    websiteLink: { icon: 'globe2', title: 'WEBSITE', containerId: 'software-webpage' },
    documentationLink: { icon: 'book', title: 'DOCUMENTATION', containerId: 'software-documentation' },
    tutorialLink: { icon: 'braces-asterisk', title: 'TUTORIALS AND USAGE', containerId: 'software-usage' }
};

async function getSiteTitle(url){
    try {
        const response = await fetch('get-external-site-title', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({'url':url})
        });
        if (!response.ok){
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (data.title) {
            return data.title;
        }
        throw new Error('Backend returned no title');
    } catch (backendError) {
        console.error('Backend method failed:', backendError.message);
        return null;
    }
}

function createTagElements(tags, className) {
    return tags.map(tag => `<span class="${className}">${tag}</span>`).join('');
}

function createLinkElements(links) {
    return Promise.all(
        Object.entries(links).map(async ([title, link]) => {
            try {
                // if title is just url, try to get real title
                let siteTitle = await getSiteTitle(link);
                // truncate long title names
                if (siteTitle && siteTitle.length > 30) {
                    siteTitle = siteTitle.slice(0, 30) + "...";
                }
                if (siteTitle){
                    return `<a target="_blank" href="${link}">${siteTitle}</a>`;
                }
                return "";
            } catch (error) {
                return "";
            }
        })
    ).then(linkElements => linkElements.join(''));
}

export function showModalForSoftware(softwareName) {
    getSoftwareModalData(softwareName).then((softwareInfo) => {
        const softwareData = formatSoftwareInfo(softwareInfo)

        $("#software-modal-title").html(softwareName)

        setupModalLayout(softwareData);
        populateModalSections(softwareData);
        // if nothing is added in the software-info section then remove it
        if ($("#software-info").children().length === 0 ) {
            $("#software-info").remove();
            $("#general-info").removeClass("col-md-7")
            $("#general-info").addClass("col-md")
        }
        populateExampleUse(softwareName);
        showModal();
    }).catch(error => {
        console.error("Unable to find software data:", error)
    })
}

function setupModalLayout(softwareData) {
    $("#software-data").append(`
        <div id="general-info" class="col-md-7">
            <div id="installed-on"></div>
            <div id="description"></div>
            <div id="core-features"></div>
            <div id="example-use"></div>
        </div>
        <div class="col-md-5" id="software-info"></div>
    `);
}

function populateModalSections(softwareData) {
    populateInstalledOn(softwareData.installedOn);
    populateDescription(softwareData.description);
    populateCoreFeatures(softwareData.coreFeatures);
    populateRelatedLinks(softwareData.relatedLinks);
    populateSimilarSoftware(softwareData.similarSoftware);
}

function populateInstalledOn(installedOn){
    if (isEmpty(installedOn)) return;

    const resources = Object.keys(installedOn);
    $("#installed-on").append(`
        <span class="section-title">INSTALLED ON</span>
        <hr class="installed-on">
    `)

    resources.forEach(resource => {
        const resource_info = installedOn[resource]
        const resourceName = resource.replace(" ", "-")
        $("#installed-on").append(`
            <div class="row section-text">
                <div id="${resourceName}-software" class="col">
                    <a target="_blank" href=${resource_info.resourceLink} >
                        <strong>${resource}</strong>
                    </a>
                </div>
                <div id="${resourceName}-software-version" class="col">
                </div>
                <hr class="installed-on">
            </div>
        `)
        if (!(isEmpty(resource_info.resourceDocumentation))) {
            $(`#${resourceName}-software`).append(`
                <a target="_blank" href=${resource_info.resourceDocumentation} >
                    <i id="${resourceName}-documentation" class="bi bi-book"></i>
                </a>
            `)
        }
        if (!(isEmpty(resource_info.resourceVersion))) {
            const versions = "v: " + resource_info.resourceVersion.join(", ");
            $(`#${resourceName}-software-version`).append(`
                ${versions}
            `)
        }
    })
}

function populateDescription(description) {
    if (isEmpty(description)) return;

    $("#description").html(`
        <p class="section-title">
            DESCRIPTION
            <img src="static/ACCESS-ai.svg" clas="ai-icon" style="max-width:15px; margin-bottom:5px;">
        </p>
        <span id="software-ai-description" class="section-text">${description}</span>
        <hr>
    `)
}

function populateCoreFeatures(coreFeatures){
    if (isEmpty(coreFeatures)) return;

    $("#core-features").html(`
        <p class="section-title">
            CORE FEATURES
            <img src="static/ACCESS-ai.svg" clas="ai-icon" style="max-width:15px; margin-bottom:5px;">
        </p>
        <span id="software-ai-core-features" class="section-text">${coreFeatures}</span>
        <hr class="installed-on">
    `)
}

async function populateRelatedLinks(relatedLinks){
    if (isEmpty(relatedLinks)) return;

    $("#software-info").append(`
        <div id="related-links" class="more-info" style="display: none;">
            <span class="intro more-info-item"><strong>Related Links</strong></span>
            <div id="software-webpage" class="more-info-item"></div>
            <div id="software-documentation" class="more-info-item"></div>
            <div id="software-usage" class="more-info-item"></div>
        </div>
    `)

    for (const [linkType, config] of Object.entries(LINK_CONFIGS)){
        if (!isEmpty(relatedLinks[linkType])){
            const linkElements = await createLinkElements(relatedLinks[linkType]);
            if (!(linkElements === "")) {
                $("#related-links").show();
                $(`#${config.containerId}`).html(`
                    <div id="${config.containerId}-title">
                        <i class="bi bi-${config.icon}"></i>
                        <span class="section-title">${config.title}</span>
                    </div>
                    <div id="${config.containerId}-link" class="section-text">
                        ${linkElements}
                    </div>
                `)
            }
        }
    }
}

function populateSimilarSoftware(similarSoftware){
    if (isEmpty(similarSoftware)) return;

    $("#software-info").append(`
        <div id="similar-software" class="more-info">
            <span class="intro more-info-item"><strong>Find Similar Software</strong></span>
        </div>
    `)
    Object.entries(SIMILAR_SOFTWARE_CONFIGS).forEach(([key, config]) => {
        if (!isEmpty(similarSoftware[key]) && (similarSoftware[key][0] != "")) {
            const containerId = `software-${key.toLocaleLowerCase()}`;
            if (key === "researchDiscipline"){
                $("#similar-software").append(`
                    <div id="${containerId}" class="more-info-item">
                        <div id="${containerId}-title">
                            <img class="bi-${config.icon}" style="width:24px; height:24px;" src="static/microscope.svg" alt="miscroscope"></img>
                            <span class="section-title">${config.title}</span>
                        </div>
                        <div class="section-text" style="vertical-align:1em";>
                            ${createTagElements(similarSoftware[key], config.className)}
                        </div>
                    </div>
                `);
            } else {
                $("#similar-software").append(`
                    <div id="${containerId}" class="more-info-item">
                        <div id="${containerId}-title">
                            <i class="bi bi-${config.icon}"></i>
                            <span class="section-title">${config.title}</span>
                        </div>
                        <div class="section-text">
                            ${createTagElements(similarSoftware[key], config.className)}
                        </div>
                    </div>
                `);
            }
        }
    });

    // remove the 'Similar Software' if nothing is added
    if ($("#similar-software").children().length === 1) {
        $("#similar-software").remove();
    }
}

function populateExampleUse(softwareName) {
    getSoftwareExampleUse(softwareName).then((softwareExampleUse) => {
        $('#example-use').append(`
            <p class="section-title">
                EXAMPLE USE
                <img src="static/ACCESS-ai.svg" clas="ai-icon" style="max-width:15px; margin-bottom:5px;">
            </p>
            <div id="software-ai-example-use" class="section-text">
                ${softwareExampleUse}
            </div>
        `);
    }).catch(error => {
        console.error("Unable to find Example Use:", error)
    })
}

function showModal() {
    const modalElement = document.getElementById('softwareDetails-modal');
    let modal = bootstrap.Modal.getInstance(modalElement);
    if (!modal) {
        modal = new bootstrap.Modal(modalElement);
    }
    modal.show();
}
