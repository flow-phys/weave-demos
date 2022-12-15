#!/bin/bash

# Numerical Resolution Study

OUT_FILE=./01_baseline_simulation/num_res/data/num_res_5_output.dsv
X_POS_INITIAL=49
Y_POS_INITIAL=50
Z_POS_INITIAL=51
X_VEL_INITIAL=5.25
Y_VEL_INITIAL=4.9
Z_VEL_INITIAL=5.0
GRAVITY=9.81
BOX_SIDE_LENGTH=100
GROUP_ID=47bcda
RUN_ID=3_5
python ./01_baseline_simulation/num_res/ball_bounce_5.py $OUT_FILE $X_POS_INITIAL $Y_POS_INITIAL $Z_POS_INITIAL $X_VEL_INITIAL $Y_VEL_INITIAL $Z_VEL_INITIAL $GRAVITY $BOX_SIDE_LENGTH $GROUP_ID $RUN_ID

OUT_FILE=./01_baseline_simulation/num_res/data/num_res_20_output.dsv
X_POS_INITIAL=49
Y_POS_INITIAL=50
Z_POS_INITIAL=51
X_VEL_INITIAL=5.25
Y_VEL_INITIAL=4.9
Z_VEL_INITIAL=5.0
GRAVITY=9.81
BOX_SIDE_LENGTH=100
GROUP_ID=47bcda
RUN_ID=3_20
python ./ball_bounce.py $OUT_FILE $X_POS_INITIAL $Y_POS_INITIAL $Z_POS_INITIAL $X_VEL_INITIAL $Y_VEL_INITIAL $Z_VEL_INITIAL $GRAVITY $BOX_SIDE_LENGTH $GROUP_ID $RUN_ID

OUT_FILE=./01_baseline_simulation/num_res/data/num_res_100_output.dsv
X_POS_INITIAL=49
Y_POS_INITIAL=50
Z_POS_INITIAL=51
X_VEL_INITIAL=5.25
Y_VEL_INITIAL=4.9
Z_VEL_INITIAL=5.0
GRAVITY=9.81
BOX_SIDE_LENGTH=100
GROUP_ID=47bcda
RUN_ID=3_100
python ./01_baseline_simulation/num_res/ball_bounce_100.py $OUT_FILE $X_POS_INITIAL $Y_POS_INITIAL $Z_POS_INITIAL $X_VEL_INITIAL $Y_VEL_INITIAL $Z_VEL_INITIAL $GRAVITY $BOX_SIDE_LENGTH $GROUP_ID $RUN_ID

python ./dsv_to_sina.py ./01_baseline_simulation/num_res/data ./01_baseline_simulation/num_res/data/num_res_output.sqlite