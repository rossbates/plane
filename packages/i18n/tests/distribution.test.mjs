import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
// Import the actual distribution, never source aliases or a mocked translator.
import { i18nInstance, initPromise } from "../dist/core/instance.js";
import { NAMESPACES } from "../dist/constants/namespaces.js";
import { SUPPORTED_LANGUAGES } from "../dist/constants/language.js";

test("packaged English renders labels, not translation keys", async () => {
  await initPromise;
  assert.equal(i18nInstance.t("auth.common.new_to_plane"), "New to Plane?");
  assert.equal(i18nInstance.t("submit"), "Submit");
});

for (const { value: language } of SUPPORTED_LANGUAGES) {
  test(`packaged ${language} loads every authoritative namespace`, async () => {
    await initPromise;
    await i18nInstance.changeLanguage(language);
    await Promise.all(
      NAMESPACES.map(async (namespace) => {
        const expected = JSON.parse(
          await readFile(new URL(`../src/locales/${language}/${namespace}.json`, import.meta.url), "utf8")
        );
        assert.equal(i18nInstance.hasResourceBundle(language, namespace), true, `${language}/${namespace} must load`);
        assert.deepEqual(i18nInstance.getResourceBundle(language, namespace), expected);
      })
    );
    const auth = i18nInstance.getResourceBundle(language, "auth");
    assert.equal(i18nInstance.t("auth.common.new_to_plane"), auth.auth.common.new_to_plane);
  });
}
