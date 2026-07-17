extends Node

signal presentation_changed(presentation: Dictionary)
signal contextual_action_changed(action: Dictionary)
signal consequence_ready(payload: Dictionary)

var presentation: Dictionary = {}
var contextual_action: Dictionary = {}
var pending_consequences: Array[Dictionary] = []
var active_consequence: Dictionary = {}
var acknowledged_presentation_ids: Dictionary = {}
var known_presentation_ids: Dictionary = {}
var notified_presentation_ids: Dictionary = {}
var delivery_paused := false
var latest_world_data: Dictionary = {}


func ingest_world_data(data: Dictionary) -> void:
	latest_world_data = data.duplicate(true)
	var next_presentation = data.get("presentation", {})
	if typeof(next_presentation) == TYPE_DICTIONARY:
		presentation = (next_presentation as Dictionary).duplicate(true)
	else:
		presentation = {}

	var next_contextual_action = presentation.get("contextual_action", null)
	if typeof(next_contextual_action) == TYPE_DICTIONARY:
		contextual_action = (next_contextual_action as Dictionary).duplicate(true)
	else:
		contextual_action = {}
	emit_signal("presentation_changed", presentation)
	emit_signal("contextual_action_changed", contextual_action)

	ingest_pending_presentations(data.get("pending_presentations", []))
	ingest_pending_presentations(presentation.get("pending_presentations", []))


func ingest_pending_presentations(values: Variant) -> void:
	if typeof(values) != TYPE_ARRAY:
		return
	for value in values:
		if typeof(value) == TYPE_DICTIONARY:
			enqueue_consequence(value)


func ingest_authoritative_events(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var outcome := _consequence_from_event(event_value)
		if not outcome.is_empty():
			enqueue_consequence(outcome)


func enqueue_consequence(payload: Dictionary) -> bool:
	var normalized := _normalize_consequence(payload)
	if normalized.is_empty():
		return false
	var presentation_id := str(normalized.get("presentation_id", ""))
	if acknowledged_presentation_ids.has(presentation_id) or known_presentation_ids.has(presentation_id):
		return false
	known_presentation_ids[presentation_id] = true
	pending_consequences.append(normalized)
	_notify_next_consequence()
	return true


func set_delivery_paused(paused: bool) -> void:
	delivery_paused = paused
	if not delivery_paused:
		_notify_next_consequence()


func has_pending_consequence() -> bool:
	return not active_consequence.is_empty() or not pending_consequences.is_empty()


func peek_next_consequence() -> Dictionary:
	if not active_consequence.is_empty():
		return active_consequence.duplicate(true)
	if pending_consequences.is_empty():
		return {}
	return pending_consequences[0].duplicate(true)


func begin_next_consequence() -> Dictionary:
	if active_consequence.is_empty() and not pending_consequences.is_empty():
		active_consequence = pending_consequences.pop_front()
	return active_consequence.duplicate(true)


func acknowledge_consequence(presentation_id: String) -> bool:
	if presentation_id.is_empty():
		return false
	acknowledged_presentation_ids[presentation_id] = true
	known_presentation_ids[presentation_id] = true
	notified_presentation_ids[presentation_id] = true
	if str(active_consequence.get("presentation_id", "")) == presentation_id:
		active_consequence = {}
	for index in range(pending_consequences.size() - 1, -1, -1):
		if str(pending_consequences[index].get("presentation_id", "")) == presentation_id:
			pending_consequences.remove_at(index)
	_notify_next_consequence()
	return true


func objective_text() -> String:
	return str(presentation.get("objective", "")).strip_edges()


func current_contextual_action() -> Dictionary:
	return contextual_action.duplicate(true)


func reset_for_fresh_world() -> void:
	presentation = {}
	contextual_action = {}
	pending_consequences.clear()
	active_consequence = {}
	acknowledged_presentation_ids.clear()
	known_presentation_ids.clear()
	notified_presentation_ids.clear()
	latest_world_data = {}
	delivery_paused = false


func _notify_next_consequence() -> void:
	if delivery_paused or not active_consequence.is_empty() or pending_consequences.is_empty():
		return
	var payload: Dictionary = pending_consequences[0]
	var presentation_id := str(payload.get("presentation_id", ""))
	if presentation_id.is_empty() or notified_presentation_ids.has(presentation_id):
		return
	notified_presentation_ids[presentation_id] = true
	emit_signal("consequence_ready", payload.duplicate(true))


func _consequence_from_event(event: Dictionary) -> Dictionary:
	var payload = event.get("payload", {})
	if typeof(payload) == TYPE_DICTIONARY:
		var embedded = payload.get("presentation", null)
		if typeof(embedded) == TYPE_DICTIONARY:
			return (embedded as Dictionary).duplicate(true)
		var outcome = payload.get("outcome", null)
		if typeof(outcome) == TYPE_DICTIONARY:
			return (outcome as Dictionary).duplicate(true)
		if payload.has("presentation_id"):
			return (payload as Dictionary).duplicate(true)
	if event.has("presentation_id"):
		return event.duplicate(true)
	return {}


func _normalize_consequence(payload: Dictionary) -> Dictionary:
	var presentation_id := str(payload.get("presentation_id", "")).strip_edges()
	var presentation_type := str(payload.get("type", payload.get("presentation_type", ""))).strip_edges()
	if presentation_id.is_empty():
		return {}
	var is_consequence := (
		"consequence" in presentation_type
		or presentation_type in ["episode_outcome", "outcome"]
		or payload.has("path")
	)
	if not is_consequence:
		return {}
	var title := str(payload.get("title", "")).strip_edges()
	var line := str(payload.get("line", "")).strip_edges()
	if title.is_empty() or line.is_empty():
		return {}
	var normalized := payload.duplicate(true)
	normalized["presentation_id"] = presentation_id
	normalized["type"] = presentation_type
	normalized["title"] = title
	normalized["line"] = line
	normalized["reaction_text"] = str(payload.get("reaction_text", "")).strip_edges()
	normalized["relationship_trend_text"] = str(payload.get("relationship_trend_text", "")).strip_edges()
	normalized["reflection_text"] = str(payload.get("reflection_text", "")).strip_edges()
	normalized["requires_server_ack"] = bool(payload.get("requires_server_ack", true))
	return normalized
