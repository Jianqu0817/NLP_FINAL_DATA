#!/usr/bin/env bash
# Archive only files belonging to this new experiment; original pilot is already local.
set -euo pipefail
cd /root/gpufree-data/nlp_final
while tmux has-session -t mech_eval 2>/dev/null; do sleep 5; done
grep -qx TRAIN_ALL_DONE mechanism_study/training.log
grep -qx EVAL_ALL_DONE mechanism_study/evaluation.log
tar -cf mechanism_study/outputs.tar -C mechanism_study runs preflight predictions training.log evaluation.log structure_test.log
echo ARCHIVE_COMPLETE
