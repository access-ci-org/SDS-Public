import {header, siteMenus, footer, footerMenus, universalMenus} from "https://esm.sh/@access-ci/ui@0.8.0"

export const siteItems = [{
    name: "ACCESS Resource Advisor",
    href: "https://access-ara.ccs.uky.edu:8080/"
}]


export const ACCESS_SUPPORT_URL = "https://support.access-ci.org/"

/*//////////////////////////////////////
    ACCESS Website Predfined Content //
*/////////////////////////////////////
export const setupFunctions = {
    universalMenus: (target) => universalMenus({
        loginUrl: "/login",
        logoutUrl: "/logout",
        siteName: "Support",
        target: target
    }),
    header: (target) => header({
        siteName: "Support",
        target: document.getElementById("header"),
        target: target
    }),
    siteMenus: (target) => siteMenus({
        items: siteItems,
        siteName: "Support",
        target: target
    }),
    footerMenus: (target) => footerMenus({
        items: siteItems,
        siteName: "Support",
        target: target
    }),
    footer: (target => footer({ target: target}))
}

export function updateNavAndHeader(){
    // Update ACCESS Support Link in ShadowHost Header
    // https://github.com/access-ci-org/access-ci-ui
    const NavShadowHost = document.getElementById('universal-menus');
    const shadowRoot = NavShadowHost.shadowRoot;
    const loginButton = shadowRoot.querySelector('li:last-child button');
    loginButton.remove();

    const HEADER_SHADOW_HOST = document.getElementById('header');
    const HEADER_SHADOW_ROOT = HEADER_SHADOW_HOST.shadowRoot;
    const ACCESS_LOGO_HREF = HEADER_SHADOW_ROOT.querySelector('.access');
    ACCESS_LOGO_HREF.href = ACCESS_SUPPORT_URL;
}