
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
    const resources = (softwareInfo["Resource"] || "").split(", ").filter(x => x.trim())
    const versions = (softwareInfo["Versions"] || "").split(", ").filter(x => x.trim())
    const resourceLink = ""
    // const resourceDocumentation = softwareInfo["RP Software Documentation" || ""].split("\n").filter(x => x.trim())
    const tutorialLinks = (softwareInfo["Example Software Use"]|| "").split("\n").filter(x => x.trim())
    const researchDiscipline = [... new Set(
            (softwareInfo["AI Research Field"]||"").split(",")
            .concat((softwareInfo["AI Research Discipline"]||"").split(","))
            .filter(x => x.trim())
        )]
    const softwareType = (softwareInfo["AI Software Type"]||"").split(",").filter(x => x.trim())
    softwareData["installedOn"] = Object.fromEntries(
        resources.map(resource => [
            resource,
            {
                resourceLink: resourceLink,
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
        "tags": (softwareInfo["AI Tags"] || "").split(",").filter(x => x.trim()),
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
            body: JSON.stringify({url:url})
        });

        if (!response.ok){
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data.title
    } catch (error) {
        console.error('Error fetching site title:', error);
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
                const displayTitle = siteTitle || link;

                if (siteTitle) {
                    return `<a target="_blank" href="${link}">${displayTitle}</a>`;
                }
                return "";
            } catch (error) {
                console.error(error)
                return `<a target="_blank" href="${link}">${link}</a>`;
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
        populateExampleUse(softwareName);
        showModal();
    }).catch(error => {
        console.error("Unable to find software data:", error)
    })
}

function setupModalLayout(softwareData) {
    if (!(isEmpty(softwareData.relatedLinks)) || !(isEmpty(softwareData.similarSoftware))) {
        $("#software-data").append(`
            <div class="col-md-7">
                <div id="installed-on"></div>
                <div id="description"></div>
                <div id="core-features"></div>
                <div id="example-use"></div>
            </div>
            <div class="col-md-5" id="software-info"></div>
        `);
    } else {
        $("#software-data").append(`
            <div class="col">
                <div id="installed-on"></div>
                <div id="description"></div>
                <div id="core-features"></div>
                <div id="example-use"></div>
            </div>
        `);
    }
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
                    <a href=${resource_info.resourceLink} >
                        <strong>${resource}</strong>
                    </a>
                </div>
                <div id="${resourceName}-software-version" class="col">
                </div>
                <hr class="installed-on">
            </div>
        `)
        if (!(isEmpty(resource_info.resourceVersion)) && resource_info.resourceVersion[0] != "") {
            $(`#${resourceName}-software-version`).append(`
                   v:
            `)
            resource_info.resourceVersion.forEach(version_command => {
                const split_vc = version_command.split("c:")
                const version = split_vc[0]
                let command = ""
                if (split_vc.length > 1) {
                    command = split_vc[1]
                }

                $(`#${resourceName}-software-version`).append(`
                    ${version}
                    <div class="text-muted small mb-2">
                        ${command}
                    </div>
                    `)
            })
        }
    })
}

function populateDescription(description) {
    if (isEmpty(description)) return;
    $("#description").html(`
        <p class="section-title">DESCRIPTION${use_ai_info === "True" ? " &#10024": ''}</p>
        <span id="software-ai-description" class="section-text">${description}</span>
        <hr>
    `)
}

function populateCoreFeatures(coreFeatures){
    if (isEmpty(coreFeatures)) return;

    $("#core-features").html(`
        <p class="section-title">CORE FEATURES${use_api ? ` &#10024`: ''}</p>
        <span id="software-ai-core-features" class="section-text">${coreFeatures}</span>
        <hr class="installed-on">
    `)
}

async function populateRelatedLinks(relatedLinks){
    if (isEmpty(relatedLinks)) return;

    $("#software-info").append(`
        <div id="related-links" class="more-info">
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
        if (!isEmpty(similarSoftware[key])) {
            const containerId = `software-${key.toLocaleLowerCase()}`;
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
    });
}

function populateExampleUse(softwareName) {
    if (use_ai_info === "False") return;
    getSoftwareExampleUse(softwareName).then((softwareExampleUse) => {
        $('#example-use').append(`
            <p class="section-title">EXAMPLE USE &#10024</p>
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