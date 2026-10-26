"""Build/content checks; uses only the Python standard library."""
import json
from html.parser import HTMLParser
from pathlib import Path
import unittest
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids, self.links, self.assets, self.headings = [], [], [], []
        self.feed(path.read_text())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))
            if attrs.get('target') == '_blank':
                assert 'noopener' in attrs.get('rel', ''), 'External tab missing noopener'
        if tag in ('script', 'img') and 'src' in attrs:
            self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') in ('stylesheet', 'icon', 'preload'):
            self.assets.append(attrs['href'])
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.headings.append(tag)


class SiteChecks(unittest.TestCase):
    def test_generated_pages_have_valid_local_destinations(self):
        paths = [ROOT/'index.html', *(ROOT/'projects'/f'{p["slug"]}.html' for p in json.loads((ROOT/'content/profile.json').read_text())['projects'])]
        for path in paths:
            with self.subTest(page=path.name):
                doc = Document(path)
                self.assertEqual(len(doc.ids), len(set(doc.ids)), 'Duplicate IDs')
                self.assertEqual(doc.headings.count('h1'), 1)
                for url in doc.links + doc.assets:
                    parsed = urlparse(url)
                    if parsed.scheme or parsed.netloc:
                        self.assertIn(parsed.scheme, ('https','http','mailto','tel'))
                        continue
                    target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                    self.assertTrue(target.is_file(), f'Missing {url} on {path.name}')
                    if parsed.fragment and target.suffix == '.html':
                        self.assertIn(parsed.fragment, Document(target).ids, f'Missing anchor {url}')

    def test_verified_content_and_research_status(self):
        text = (ROOT/'index.html').read_text()
        for phrase in ('December 2025 – Present', 'March 2024 – October 2025', 'October 2021 – September 2023', '50–60%', '40%', '100K+', '30%', '35%', 'Munich, Germany', 'murtazazaidi.tech@gmail.com', 'Research in progress'):
            self.assertIn(phrase, text)
        research = (ROOT/'projects/inference-routing.html').read_text()
        self.assertIn('completed performance results are not yet reported', research)
        for obsolete in ('murtazazaidi1@outlook.com', 'syedmurtazazaidi/', 'Oct 2023 — Present'):
            self.assertNotIn(obsolete, text)

    def test_archive_and_resume_are_preserved(self):
        archive = json.loads((ROOT/'content/archive.json').read_text())
        self.assertEqual(len(archive['projects']), 11)
        self.assertEqual(len(archive['certifications']), 6)
        text = (ROOT/'index.html').read_text()
        for project in archive['projects']:
            self.assertIn(project['href'], text)
            self.assertTrue((ROOT/project['href']).is_file())
        self.assertTrue((ROOT/'assets/documents/previous-resume.pdf').read_bytes().startswith(b'%PDF'))
        if not (ROOT/'resume.pdf').exists() and not (ROOT/'MURTAZA_ZAIDI_RESUME.pdf').exists():
            self.assertIn('Download previous résumé', text)
            self.assertIn('existing PDF is an earlier version', text)

    def test_clean_production_output(self):
        self.assertTrue((ROOT/'dist/index.html').exists())
        for hidden in ('.git', '.aws', '.codex', '.agents', 'content', 'scripts', 'tests'):
            self.assertFalse((ROOT/'dist'/hidden).exists())
        self.assertEqual((ROOT/'index.html').read_bytes(), (ROOT/'dist/index.html').read_bytes())


if __name__ == '__main__':
    unittest.main(verbosity=2)
