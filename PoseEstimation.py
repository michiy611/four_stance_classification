import cv2
import mediapipe as mp
import time
import streamlit as st

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose
mp_holistic = mp.solutions.holistic

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

kneeStartFlag = kneeEndFlag = calfStartFlag = calfEndFlag = outsideFlag = insideFlag = False
prevTime = 0
step = 0
camera = True

# 手首と膝の固定関数
def fixed_point(results, currTime, prevSetTime, startFlag, step):
    if (results.pose_landmarks.landmark[16].y <= results.pose_landmarks.landmark[26].y + 0.1) \
                        and (results.pose_landmarks.landmark[16].y >= results.pose_landmarks.landmark[26].y - 0.1):

        # 固定が開始されていなければ、開始
        if not startFlag:
            # 固定を開始した時間を保存
            prevSetTime = currTime
            # 開始状態にする
            startFlag = True
        # 開始されており、3秒経過すれば、次のステップに
        else:
            # 3秒固定で次のステップに遷移
            time_loc.header(f'{currTime - prevSetTime:.1f}s / 3s')
            if (currTime - prevSetTime) >= 3:
                step += 1
    else:
        # 座標がずれたらリセット
        prevSetTime = 0
        startFlag = False
    
    return prevSetTime, startFlag, step

with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as pose:
    st.title('4stance Type Checker')
    text_loc = st.empty()
    image_loc = st.empty()
    time_loc = st.empty()

    if st.button('Start'):
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                print("Ignoring empty camera frame.")
                continue

            # BGR -> RGB.
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # パフォーマンスを向上させるために、imageを書込み不可に
            # 参照渡し
            image.flags.writeable = False
            results = pose.process(image)

            # 画像にランドマークを描画
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            mp_drawing.draw_landmarks(
                image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            

            currTime = time.time()
            fps = 1 / (currTime - prevTime)
            prevTime = currTime

            # fpsの描画
            cv2.putText(image, f'FPS: {int(fps)}', (20, 70), cv2.FONT_HERSHEY_PLAIN, 2, (255, 60, 60), 2)

            if step == 0:
                showTime = currTime
                step += 1

            # タイプ[A, B]の判定

            # ~10s 最初の指示
            if step == 1:
                if (currTime - showTime) < 10:
                    text_loc.info('最初に、タイプAかタイプBのどちらかを判別します。\n全身が写るようにし、左を向いてください。')
                else:
                    step += 1

            # 膝の前面に手を置いて前屈
            # 膝の前側に手を置いて3秒待つ
            if step == 2:
                text_loc.info('膝の前側に手を置いて3秒待ってください。')
                prevSetTime, kneeStartFlag, step = fixed_point(results, currTime, prevSetTime, kneeStartFlag, step)

            # 前屈して、最大の場所で5秒待つ
            if step == 3:
                text_loc.info('前屈して、最大の場所で5秒待ってください。')
                if not kneeEndFlag:
                    setPoint = results.pose_landmarks.landmark[16].y
                    prevSetTime = currTime
                    kneeEndFlag = True
                else:
                    time_loc.header(f'{currTime - prevSetTime:.1f}s / 5s')
                    if (currTime - prevSetTime) >= 5:
                        shinDepth = results.pose_landmarks.landmark[16].y - results.pose_landmarks.landmark[28].y
                        step += 1
                    if abs(setPoint - results.pose_landmarks.landmark[16].y) >= 0.05:
                        kneeEndFlag = False

            # 膝の後ろ側に手を置いて3秒待つ
            if step == 4:
                text_loc.info('膝の後ろ側に手を置いて3秒待ってください。')
                prevSetTime, calfStartFlag, step = fixed_point(results, currTime, prevSetTime, calfStartFlag, step)


            if step == 5:
                text_loc.info('前屈して、最大の場所で5秒待ってください。')
                if not calfEndFlag:
                    setPoint = results.pose_landmarks.landmark[16].y
                    prevSetTime = currTime
                    calfEndFlag = True
                else:
                    time_loc.header(f'{currTime - prevSetTime:.1f}s / 5s')
                    if (currTime - prevSetTime) >= 5:
                        calfDepth = results.pose_landmarks.landmark[16].y - results.pose_landmarks.landmark[28].y
                        showTime = currTime
                        step += 1
                    if abs(setPoint - results.pose_landmarks.landmark[16].y) >= 0.05:
                        calfEndFlag = False

            if step == 6:
                if (currTime - showTime) < 10:
                    if (shinDepth - calfDepth) >= 0:
                        text_loc.success('あなたのタイプはAです。')
                        firsttype = 'A'
                    else:
                        text_loc.success('あなたのタイプはBです。')
                        firsttype = 'B'
                else:
                    showTime = currTime
                    step += 1


            # タイプ[A, B]の判定
            
            if step == 7:
                if (currTime - showTime) < 10:
                    text_loc.info('次に、タイプ1かタイプ2のどちらかを判別します。\n足を肩幅に開き、胸の前で両手をあわせてください。')
                else:
                    step += 1

            # type1
            if step == 8:
                text_loc.info('足裏の外側(小指側)を浮かせて、内側に体重がかかるようにしてください。\nそのまま身体を限界までねじり、5秒待ってください。')
                length = abs(results.pose_landmarks.landmark[11].x - results.pose_landmarks.landmark[12].x)
                if not insideFlag:
                    prevSetTime = currTime
                    setPoint = length
                    insideFlag = True
                else:
                    time_loc.header(f'{currTime - prevSetTime:.1f}s / 5s')
                    if (currTime - prevSetTime) >= 5:
                        insideTwist = setPoint
                        step += 1
                    if (length >= setPoint + 0.05) or (length <= setPoint - 0.05):
                        insideFlag = False

            # type2
            if step == 9:
                text_loc.info('足裏の内側(親指側)を浮かせて、外側に体重がかかるようにしてください。\nそのまま身体を限界までねじり、5秒待ってください。')
                length = abs(results.pose_landmarks.landmark[11].x - results.pose_landmarks.landmark[12].x)
                if not outsideFlag:
                    prevSetTime = currTime
                    setPoint = length
                    outsideFlag = True
                else:
                    time_loc.header(f'{currTime - prevSetTime:.1f}s / 5s')
                    if (currTime - prevSetTime) >= 5:
                        outsideTwist = setPoint
                        showTime = currTime
                        step += 1
                    if (length >= setPoint + 0.05) or (length <= setPoint - 0.05):
                        outsideFlag = False

            # type [1, 2] の判定
            if step == 10:
                if (currTime - showTime) < 5:
                    if insideTwist <= outsideTwist:
                        text_loc.success('あなたのタイプは1です。')
                        secondtype = 1
                    else:
                        text_loc.success('あなたのタイプは2です。')
                        secondtype = 2
                else:
                    showTime = currTime
                    step += 1

            if step == 11:
                text_loc.success(f'あなたのタイプは {firsttype}{secondtype} です。')

            image_loc.image(image)
            if cv2.waitKey(5) & 0xFF == 27:
                break
        cap.release()







# 精度の実験（条件を変えて）
# 1，2　横を向いた状態からのほうが
# アピールポイント