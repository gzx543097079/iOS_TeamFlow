extends Control

var score: int = 0
var game_paused: bool = false

@onready var score_label: Label = $Center/Actions/Score
@onready var pause_button: Button = $Center/Actions/Pause


func collect() -> void:
	# 暂停状态由当前场景持有，输入不得绕过暂停规则。
	if game_paused:
		return
	score += 1
	score_label.text = "Score: %d" % score


func toggle_pause() -> void:
	game_paused = not game_paused
	pause_button.text = "Resume" if game_paused else "Pause"
