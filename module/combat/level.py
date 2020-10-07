from module.base.base import ModuleBase
from module.base.button import *
from module.base.decorator import Config
from module.logger import logger
from module.ocr.ocr import Ocr

LV_GRID_MAIN = ButtonGrid(origin=(58, 118), delta=(0, 100), button_shape=(46, 19), grid_shape=(1, 3))
LV_GRID_VANGUARD = ButtonGrid(origin=(58, 420), delta=(0, 100), button_shape=(46, 19), grid_shape=(1, 3))
LV_BUTTONS = LV_GRID_MAIN.buttons() + LV_GRID_VANGUARD.buttons()
COLOR_WHITE = (255, 255, 255)
COLOR_MASKED = (107, 105, 107)


class Level(ModuleBase):
    _lv = []
    _lv_before_battle=[]

    @property
    def lv(self):
        """
        Returns:
            list[int]:
        """
        return self._lv

    @lv.setter
    def lv(self, value):
        """
        Args:
            value (list[int]):
        """
        self._lv = value

    def lv_reset(self):
        """
        Call this method after enter map.
        """
        self._lv = [-1] * 6
        self._lv_before_battle = [-1] * 6

    def lv_get(self, after_battle=False):
        """
        Args:
            after_battle (bool): True if called after battle else False.

        Returns:
            list[int]:
        """
        if not self.config.STOP_IF_REACH_LV120:
            return [-1] * 6

        self._lv_before_battle = self.lv if after_battle else [-1] * 6

        ocr = LevelOcr(LV_BUTTONS)
        self.lv = ocr.ocr(self.device.image)
        logger.attr('LEVEL', ', '.join(str(data) for data in self.lv))

        if after_battle:
            self.lv120_triggered()

        return self.lv

    def lv120_triggered(self):
        if not self.config.STOP_IF_REACH_LV120:
            return False

        for i in range(6):
            if self.lv[i] == 120 and self._lv_before_battle[i] == 119:
                logger.info(f'Position {i} LV.120 Reached')
                self.config.LV120_TRIGGERED = True
                return True

        return False

class LevelOcr(Ocr):
    # Ocr's default argument 'threshold=128' makes some digits too thin to be recognized.
    # Use 'threshold=191' instead.
    def __init__(self, buttons, lang='azur_lane', letter=COLOR_WHITE, threshold=191, alphabet='0123456789',
                 name='LevelOcr'):
        super().__init__(buttons, lang=lang, letter=letter, threshold=threshold, alphabet=alphabet, name=name)

    def pre_process(self, image):
        # Check the max value of red channel to find out whether the image is masked.
        # It would be no larger than COLOR_MASKED[0]=107 iff masked.
        # Crop before checking to cut off the "need repair" icon while preserving upper part of char 'V'.
        max_red = image[:8, :, 0].max()
        if max_red <= COLOR_MASKED[0]:
            # The mask on low hp ships turns COLOR_WHITE=(255, 255, 255) to COLOR_MASKED=(107, 105, 107),
            # so multiply all channels by a scalar can turn them back.
            scalar = np.mean(COLOR_WHITE) / np.mean(COLOR_MASKED)
            image = cv2.addWeighted(image, scalar, image, 0, 0)

        image = super().pre_process(image)
        # Find 'L' to strip 'LV.'.
        # Ruturn an empty image if 'L' is not found.
        letter_l = np.nonzero(image[2:15, :].max(axis=0) < 127)[0]
        if len(letter_l):
            return image[:, letter_l[0] + 17:]
        else:
            return np.array([[255]], dtype=np.uint8)

    def after_process(self, result):
        result = super().after_process(result)

        return int(result) if result else -1
