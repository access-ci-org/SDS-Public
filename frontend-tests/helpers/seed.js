// Helpers for seeding the Flask test database via /__test__/seed.

export const DEFAULT_ADMIN = { username: "admin1", password: "adminpass" };
export const DEFAULT_USER = { username: "user1", password: "userpass" };

export const BASE_USERS = [
    { ...DEFAULT_ADMIN, is_admin: true },
    { ...DEFAULT_USER, is_admin: false },
];

export const BASE_SOFTWARE = {
    name: "testpkg",
    description: "A test package",
    ai: {
        ai_description: "AI description for testpkg",
        ai_general_tags: "test, pkg",
        ai_software_type: "library",
        ai_research_discipline: "Computer Science",
    },
    resources: [
        {
            resource: "test_cluster",
            version: "1.0.0",
            command: "module load testpkg/1.0.0",
        },
    ],
};

export const BASE_PAYLOAD = {
    users: BASE_USERS,
    resources: ["test_cluster"],
    software: [BASE_SOFTWARE],
};

/**
 * Wipe and re-seed the test database. `overrides` is merged shallowly
 * onto BASE_PAYLOAD — pass new arrays to fully replace any field.
 */
export async function seed(request, overrides = {}) {
    const payload = { ...BASE_PAYLOAD, ...overrides };
    const resp = await request.post("/__test__/seed", { data: payload });
    if (!resp.ok()) {
        throw new Error(`Seed failed: ${resp.status()} ${await resp.text()}`);
    }
}
