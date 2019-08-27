"""
TODO: Add drawn on grid, undo feature, spot erase feature.
Program that
"""
import security
import requests
from quickdraw import QuickDrawData
from PIL import Image
import azure.cognitiveservices.speech as speechsdk


def image_recognizer(image_url: str):
    """
    Takes in an image from a url and outputs objects detected by Microsoft Azure
    """

    vision_base_url = "https://eastus.api.cognitive.microsoft.com/vision/v2.0/"
    analyze_url = vision_base_url + "analyze"
    headers = {'Ocp-Apim-Subscription-Key': security.azure_key}
    params = {'visualFeatures': 'Categories,Description,Objects'}
    data = {'url': image_url}
    response = requests.post(analyze_url, headers=headers, params=params, json=data)
    response.raise_for_status()
    analysis = response.json()

    output_dict = {}
    output_dict["categories"] = analysis["categories"]
    output_dict["objects"] = analysis["objects"]
    output_dict["description"] = analysis["description"]
    print(analysis["categories"])
    print(analysis["objects"])
    print(analysis["description"])
    return output_dict


def speech_recognize():
    """
    Keywords:
    - Erase, to erase the drawing
    - "Noun" on x dot y, to place a noun at that coordinate. i.e. "Tree at 3.4."
    - Noun across/down point x/y, to fill a row or column i.e. "Mountain across .5."
    """
    speech_key, service_region = security.azure_speech_key, "eastus"
    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)

    # Creates a recognizer with the given settings
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config)

    print("Say something...")
    result = speech_recognizer.recognize_once()

    # Checks result.
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print("Recognized: {}".format(result.text))
        return result.text

    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized: {}".format(result.no_match_details))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech Recognition canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))
    return ""


def keyword_finder(speech: str) -> list:
    """
    Attempts to find command phrases in the speech transcript.
    ex:
    >>> keyword_finder("Nose at 6.3.")
    >>> ["Nose", (6,3), 0]
    """
    said = speech
    if said[:-1] == "Erase":
        return ["Erase", (-1, -1), 0]

    # Get in form of number dot number
    potential = (said[-4], said[-2])
    said = said.strip()
    noun = said.split()[0]
    print(said)
    if speech[-2].isdigit():
        digit = int(speech[-2])
        print(digit + 2)
        if "row" in said or "road" in said or "across" in said:
            return [noun, (0, digit), 1]
        elif "column" in said or "down" in said:
            return [noun, (digit, 0), 2]

    if potential[0].isdigit() and potential[1].isdigit():
        coordinate = (int(potential[0]), int(potential[1]))
        output = [noun, coordinate, 0]
        print(coordinate)
        return output


def bad_sketch(keyword: str) -> str:
    """
    Input a noun you want a sketch of, and if Google Quickdraw finds it,
    it will save a random doodle of it to keyword.gif, and return the filepath.
    """
    qd = QuickDrawData()
    if keyword is not None:
        keyword = keyword.lower()
        if keyword == "person":
            keyword = "smiley face"
    try:
        key = qd.get_drawing(keyword)
        filepath = "keyword.gif"
        key.image.save(filepath)
        return filepath
    except ValueError:
        return "blank.png"


def pic_to_doodle(input_path: str):
    """
    The main function, put in an image, and it outputs a sketch
    """
    if input_path != "":
        azure_dict = image_recognizer(input_path)
        erase_image("image.png")
        for obj in azure_dict["objects"]:
            print("ab")
            noun = obj["object"]

            xcor = obj["rectangle"]["x"] + 750
            ycor = obj["rectangle"]["y"] + 850
            if bad_sketch(noun) is not None:
                print("ba")
                add_to_drawing(noun, (xcor, ycor))
                if noun == "person":
                    add_to_drawing("t-shirt", (xcor, ycor + 200))
            else:
                if "parent" in obj:
                    parent = obj["parent"]["object"]
                    if bad_sketch(parent) is not None:
                        add_to_drawing(parent, (xcor, ycor))


def speech_to_doodle(to_draw=""):
    """
    Speak to draw, using Azure voice recognition
    You can use voice commands to erase the image,
    place an image onto a part of the grid,
     or fill a row or column with something
    """
    if to_draw == "":
        to_draw = keyword_finder(speech_recognize())

    if to_draw is not None:
        noun = to_draw[0].lower()
        noun = speech_correction(noun)
        xcor = to_draw[1][0]
        ycor = to_draw[1][1]
        fill = to_draw[2]
        if noun == "erase":
            erase_image("image.png")
        elif fill == 1:
            grid_fill(True, ycor, noun)
        elif fill == 2:
            grid_fill(False, xcor, noun)
        else:
            grid_draw(xcor, ycor, noun)
        return to_draw
    else:
        print("Sorry! Couldn't catch that.")


def speech_correction(noun):
    """
    Corrects common misheard words. If you have any, add it to the dictionary!
    """
    misheard_dict = {"son": "sun", "shirt": "t-shirt", "smiley": "smiley face", "year": "ear",
                     "frying": "frying pan", "free": "tree", "suck": "sock", "nodes": "nose"}
    return misheard_dict[noun] if noun in misheard_dict else noun


def add_to_drawing(word: str, xytuple: tuple):
    """
    This is what puts images into a communal drawing
    """
    filepath = bad_sketch(word)
    img = Image.open(filepath, 'r')
    #background = Image.new('RGBA', (2600, 2000), (255, 255, 255, 255))
    background = Image.open("image.png", "r")
    background.paste(img, xytuple)
    background.save('image.png', "PNG")


def erase_image(image_name):
    """
    Replaces image with a blank image.
    """
    background = Image.new('RGBA', (2000, 2000), (255, 255, 255, 255))
    background.save(image_name, "PNG")


def grid_to_pixel(x, y):
    """
    Converts grid coordinates into pixel coordinates
    """
    horiz = x * 250 + 100
    vert = y * 300 + 100
    return (horiz, vert)


def grid_draw(x, y, word):
    """
    Takes in Cartesian coordinates, and plots onto image
    """
    pixel_coor = grid_to_pixel(x, y)
    print(pixel_coor[0])
    add_to_drawing(word, pixel_coor)


def grid_fill(row: bool, coordinate, word: str):
    """
    Fill a row or column with the given word
    """

    if row:
        num = 0
        while num <= 10:
            pixel_coor = grid_to_pixel(num, coordinate)
            add_to_drawing(word, pixel_coor)
            num += 1
    else:
        num = 8
        while num > 0:
            pixel_coor = grid_to_pixel(coordinate, num)
            add_to_drawing(word, pixel_coor)
            num -= 1


if __name__ == '__main__':

    #image_recognizer("bob")
    #print(thesaurize("plant"))
    #bad_sketch("smiley face")
    #add_to_drawing("star", (0, 500))
    #dream("blah", "blah")
    # num = 100
    # while num <= 2100:
    #     shift_to_drawing("tree", num, 900)
    #     num += 200

    # num = 0
    # while num < 10:
    #     grid_draw(num, 2, "skull")
    #     num += 1
    #grid_fill(False, 4, "mountain")
    #speech_to_doodle("blach")
 # img = Image.new('RGB', (50, 50), (255, 255, 255))
 # img.save("blank.png", "PNG")
    pass

"""
[{'name': 'plant_tree', 'score': 0.984375}]
[{'rectangle': {'x': 161, 'y': 88, 'w': 680, 'h': 458}, 'object': 'tree', 'confidence': 0.837, 'parent': {'object': 'plant', 'confidence': 0.876}}]
{'tags': ['grass', 'outdoor', 'water', 'field', 'green', 'cow', 'tree', 'herd', 'grassy', 'lake', 'grazing', 'body', 'large', 'bench', 'front', 'lush', 'cattle', 'riding', 'view', 'sheep', 'river', 'standing', 'mountain', 'street', 'walking', 'motorcycle', 'man', 'boat', 'sunset', 'sign', 'red', 'bird', 'hill', 'ocean', 'parked', 'flying', 'elephant', 'horse', 'blue', 'white'], 'captions': [{'text': 'a large green field with trees in the background', 'confidence': 0.9170250836752474}]}
"""


"""
Funny urls:
https://adobe99u.files.wordpress.com/2018/01/antonio-guillem-girl-winning-good-news-stock-photography.jpg?quality=100&w=1640&h=1200

https://previews.123rf.com/images/stockbroker/stockbroker1111/stockbroker111100001/11183288-business-meeting-in-an-office.jpg
"""