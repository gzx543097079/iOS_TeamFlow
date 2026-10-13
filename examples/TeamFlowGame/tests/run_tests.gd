extends SceneTree

var failures: int = 0


func _initialize() -> void:
	call_deferred("run_tests")


func check(condition: bool, message: String) -> void:
	if not condition:
		failures += 1
		push_error(message)


func run_tests() -> void:
	var scene: PackedScene = load("res://main.tscn")
	if scene == null:
		push_error("主场景加载失败")
		quit(1)
		return
	var game = scene.instantiate()
	root.add_child(game)
	await process_frame
	var collect_button: Button = game.get_node("Center/Actions/Collect")
	var pause_button: Button = game.get_node("Center/Actions/Pause")
	var score_label: Label = game.get_node("Center/Actions/Score")
	collect_button.pressed.emit()
	check(game.score == 1 and score_label.text == "Score: 1", "按钮应更新分数与显示")
	pause_button.pressed.emit()
	collect_button.pressed.emit()
	check(game.score == 1 and pause_button.text == "Resume", "暂停后不得继续计分")
	pause_button.pressed.emit()
	collect_button.pressed.emit()
	check(game.score == 2, "恢复后应能继续计分")
	game.queue_free()
	await process_frame
	var restarted = scene.instantiate()
	root.add_child(restarted)
	await process_frame
	check(restarted.score == 0 and not restarted.game_paused, "重新进入场景应重置本局状态")
	restarted.queue_free()
	await process_frame
	print("场景行为测试：%s" % ("通过" if failures == 0 else "失败"))
	quit(0 if failures == 0 else 1)
