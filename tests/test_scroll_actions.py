"""Offline pointer/scroll contract: never discard the requested wheel position."""
import unittest
from unittest.mock import MagicMock,call

from sqbf.models import validate_action,ActionValidationError
from sqbf.runner import apply_action


class ScrollTests(unittest.TestCase):
    def test_explicit_coordinates_move_pointer_before_wheel(self):
        page=MagicMock()
        apply_action(page,{'action':'scroll','x':1150,'y':724,'amount':545})
        self.assertEqual(page.mouse.mock_calls,[call.move(1150,724),call.wheel(0,545)])

    def test_legacy_scroll_without_coordinates_is_unchanged(self):
        page=MagicMock();apply_action(page,{'action':'scroll','amount':400})
        self.assertEqual(page.mouse.mock_calls,[call.wheel(0,400)])

    def test_invalid_or_incomplete_scroll_coordinates_are_rejected(self):
        for fields in ({'x':1},{'y':1},{'x':-1,'y':2},{'x':1280,'y':2},
                       {'x':1,'y':800},{'x':'10','y':1},{'x':float('nan'),'y':1}):
            with self.subTest(fields=fields),self.assertRaises(ActionValidationError):
                validate_action({'action':'scroll','amount':400,**fields},1280,800)

    def test_scroll_elsewhere_preserves_focused_numeric_value(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':800})
            page.set_content('''<div style="height:2500px"><input id="grain" type="number" step="0.1" value="45"
              style="position:absolute;left:350px;top:300px"></div>
              <script>document.querySelector('input').addEventListener('wheel', e=>{
                e.preventDefault();e.target.value=(Number(e.target.value)-(e.deltaY>0?0.1:-0.1)).toFixed(1);
              },{passive:false});</script>''')
            page.locator('#grain').click()
            apply_action(page,{'action':'scroll','x':1150,'y':724,'amount':545})
            page.wait_for_timeout(300)
            self.assertEqual(page.locator('#grain').input_value(),'45')
            self.assertGreater(page.evaluate('window.scrollY'),0)
            browser.close()
