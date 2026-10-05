from unittest.mock import patch

from django.test import SimpleTestCase

from rdgenerator.forms import GenerateForm
from rdgenerator.versions import (
    FALLBACK_VERSIONS,
    _build_choices,
    _is_release_tag,
    get_version_choices,
)


class VersionChoiceTests(SimpleTestCase):
    def setUp(self):
        import rdgenerator.versions as versions_mod
        versions_mod._cached_choices = None
        versions_mod._cached_default = None
        versions_mod._cached_at = 0

    def test_release_tag_filter(self):
        self.assertTrue(_is_release_tag("1.5.0", False, False))
        self.assertTrue(_is_release_tag("1.4.9", False, False))
        self.assertFalse(_is_release_tag("nightly", True, False))
        self.assertFalse(_is_release_tag("1.5.0", True, False))
        self.assertFalse(_is_release_tag("1.5.0", False, True))
        self.assertFalse(_is_release_tag("beta", False, False))

    def test_build_choices_puts_nightly_first(self):
        choices = _build_choices(["1.5.0", "1.4.9"])
        self.assertEqual(choices[0], ("master", "nightly"))
        self.assertEqual(choices[1], ("1.5.0", "1.5.0"))
        self.assertEqual(choices[2], ("1.4.9", "1.4.9"))

    @patch("rdgenerator.versions.fetch_official_versions")
    def test_get_version_choices_uses_official_releases(self, mock_fetch):
        mock_fetch.return_value = ["1.5.0", "1.4.9"]
        choices, default = get_version_choices(force_refresh=True)
        self.assertEqual(default, "1.5.0")
        self.assertIn(("master", "nightly"), choices)
        self.assertIn(("1.5.0", "1.5.0"), choices)
        self.assertIn(("1.4.9", "1.4.9"), choices)

    @patch("rdgenerator.versions.fetch_official_versions")
    def test_get_version_choices_falls_back_when_github_fails(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("network down")
        choices, default = get_version_choices(force_refresh=True)
        self.assertEqual(default, FALLBACK_VERSIONS[0])
        self.assertEqual(choices[0], ("master", "nightly"))
        self.assertEqual(choices[1], (FALLBACK_VERSIONS[0], FALLBACK_VERSIONS[0]))

    @patch("rdgenerator.forms.get_version_choices")
    def test_form_uses_dynamic_version_choices(self, mock_get_choices):
        mock_get_choices.return_value = (
            [("master", "nightly"), ("1.5.0", "1.5.0"), ("1.4.9", "1.4.9")],
            "1.5.0",
        )
        form = GenerateForm()
        self.assertEqual(form.fields["version"].initial, "1.5.0")
        self.assertEqual(
            list(form.fields["version"].choices),
            [("master", "nightly"), ("1.5.0", "1.5.0"), ("1.4.9", "1.4.9")],
        )
