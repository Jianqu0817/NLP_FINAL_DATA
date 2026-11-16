#!/usr/bin/env bash
# Start only after the training command (tmux mech_train) exits successfully.
set -euo pipefail
cd /root/gpufree-data/nlp_final
while tmux has-session -t mech_train 2>/dev/null; do sleep 5; done
grep -qx TRAIN_ALL_DONE mechanism_study/training.log
for v in Base A C B D E; do
    datasets=(confirm_original confirm_wording confirm_order)
    if [[ $v == B || $v == D || $v == E ]]; then datasets+=(old_original old_paraphrase); fi
    .venv/bin/python -u mechanism_study/run_eval.py "$v" "${datasets[@]}"
done
echo EVAL_ALL_DONE
