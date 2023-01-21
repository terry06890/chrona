import unittest
from unittest.mock import Mock, patch
import tempfile
import os

from tests.common import createTestDbTable, readTestDbTable
from hist_data.enwiki.download_img_license_info import downloadInfo

TEST_RESPONSE1 = {
  'batchcomplete': '',
  'query': {
    'normalized': [
      {
        'from': 'File:Georgia_Aquarium_-_Giant_Grouper_edit.jpg',
        'to': 'File:Georgia Aquarium - Giant Grouper edit.jpg'
      }
    ],
    'pages': {
      '-1': {
        'ns': 6,
        'title': 'File:Octopus2.jpg',
        'missing': '',
        'known': '',
        'imagerepository': 'shared',
        'imageinfo': [
          {
            'url': 'https://upload.wikimedia.org/wikipedia/commons/5/57/Octopus2.jpg',
            'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Octopus2.jpg',
            'descriptionshorturl': 'https://commons.wikimedia.org/w/index.php?curid=2795257',
            'extmetadata': {
              'Credit': {
                'value': '<span class=\\"int-own-work\\" lang=\\"en\\">Own work</span>',
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Artist': {
                'value': 'albert kok',
                'source': 'commons-desc-page'
              },
              'LicenseShortName': {
                'value': 'CC BY-SA 3.0',
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Restrictions': {
                'value': '',
                'source': 'commons-desc-page',
                'hidden': ''
              }
            }
          }
        ]
      }
    }
  }
}

TEST_RESPONSE2 = {
  'batchcomplete': '',
  'query': {
    'normalized': [
      {
        'from': 'File:Georgia_Aquarium_-_Giant_Grouper_edit.jpg',
        'to': 'File:Georgia Aquarium - Giant Grouper edit.jpg'
      }
    ],
    'pages': {
      '-1': {
        'ns': 6,
        'title': 'File:Octopus2.jpg',
        'missing': '',
        'known': '',
        'imagerepository': 'shared',
        'imageinfo': [
          {
            'url': 'https://upload.wikimedia.org/wikipedia/commons/5/57/Octopus2.jpg',
            'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Octopus2.jpg',
            'descriptionshorturl': 'https://commons.wikimedia.org/w/index.php?curid=2795257',
            'extmetadata': {
              'Credit': {
                'value': '<span class=\\"int-own-work\\" lang=\\"en\\">Own work</span>',
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Artist': {
                'value': 'albert kok',
                'source': 'commons-desc-page'
              },
              'LicenseShortName': {
                'value': 'CC BY-SA 3.0',
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Restrictions': {
                'value': '',
                'source': 'commons-desc-page',
                'hidden': ''
              }
            }
          }
        ]
      },
      '-2': {
        'ns': 6,
        'title': 'File:Georgia Aquarium - Giant Grouper edit.jpg',
        'missing': '',
        'known': '',
        'imagerepository': 'shared',
        'imageinfo': [
          {
            'url': 'https://upload.wikimedia.org/wikipedia/commons/2/23/Georgia_Aquarium_-_Giant_Grouper_edit.jpg',
            'descriptionurl': 'https://commons.wikimedia.org/wiki/File:Georgia_Aquarium_-_Giant_Grouper_edit.jpg',
            'descriptionshorturl': 'https://commons.wikimedia.org/w/index.php?curid=823649',
            'extmetadata': {
              'Credit': {
                "value": "<a href=\"//commons.wikimedia.org/wiki/File:Georgia_Aquarium_-_Giant_Grouper.jpg\" title=\"File:Georgia Aquarium - Giant Grouper.jpg\">File:Georgia Aquarium - Giant Grouper.jpg</a>",
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Artist': {
                "value": "Taken by <a href=\"//commons.wikimedia.org/wiki/User:Diliff\" title=\"User:Diliff\">Diliff</a> Edited by <a href=\"//commons.wikimedia.org/wiki/User:Fir0002\" title=\"User:Fir0002\">Fir0002</a>",
                'source': 'commons-desc-page'
              },
              'LicenseShortName': {
                'value': 'CC BY 2.5',
                'source': 'commons-desc-page',
                'hidden': ''
              },
              'Restrictions': {
                'value': '',
                'source': 'commons-desc-page',
                'hidden': ''
              }
            }
          }
        ]
      }
    }
  }
}

class TestDownloadInfo(unittest.TestCase):
	@patch('requests.get', autospec=True)
	def test_download(self, requestsGetMock):
		requestsGetMock.side_effect = [Mock(json=lambda: TEST_RESPONSE1), Mock(json=lambda: TEST_RESPONSE2)]
		with tempfile.TemporaryDirectory() as tempDir:
			# Create temp image-data db
			imgDb = os.path.join(tempDir, 'img_data.db')
			createTestDbTable(
				imgDb,
				'CREATE TABLE page_imgs (page_id INT PRIMARY KEY, img_name TEXT)',
				'INSERT into page_imgs VALUES (?, ?)',
				{
					(1, 'Octopus2.jpg'),
				}
			)

			# Run
			downloadInfo(imgDb)
			# Check
			self.assertEqual(
				readTestDbTable(imgDb, 'SELECT id, name, license, artist, credit, restrictions, url from imgs'),
				{
					(1, 'Octopus2.jpg', 'CC BY-SA 3.0', 'albert kok', 'Own work', '',
						'https://upload.wikimedia.org/wikipedia/commons/5/57/Octopus2.jpg'),
				}
			)

			# Run with updated image-data db
			createTestDbTable(
				imgDb,
				None,
				'INSERT into page_imgs VALUES (?, ?)',
				{
					(2, 'Georgia_Aquarium_-_Giant_Grouper_edit.jpg'),
				}
			)
			downloadInfo(imgDb)
			# Check
			self.assertEqual(
				readTestDbTable(imgDb, 'SELECT id, name, license, artist, credit, restrictions, url from imgs'),
				{
					(1, 'Octopus2.jpg', 'CC BY-SA 3.0', 'albert kok', 'Own work', '',
						'https://upload.wikimedia.org/wikipedia/commons/5/57/Octopus2.jpg'),
					(2, 'Georgia_Aquarium_-_Giant_Grouper_edit.jpg', 'CC BY 2.5', 'Taken by Diliff Edited by Fir0002',
						'File:Georgia Aquarium - Giant Grouper.jpg', '', 'https://upload.wikimedia.org/' \
							'wikipedia/commons/2/23/Georgia_Aquarium_-_Giant_Grouper_edit.jpg'),
				}
			)
