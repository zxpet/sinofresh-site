<?php
/**
 * Normalising dumper for the Gravity Forms -> Fluent Forms migration.
 *
 * Both sides are reduced to the SAME shape so the comparison in
 * tools/b3h_form_migration_check.py can be a plain structural diff instead of
 * two ad-hoc parsers that might each be wrong in the same direction.
 *
 *   { "gf": { "<id>": {title, fields:[{type,label,required,choices}], notifications:[{to,subject,event}]} },
 *     "ff": { "<id>": {                                    ... same ...
 *                       active: true } },
 *     "ff_notification_rows": { "<form_id>": <row count for meta_key=notifications> },
 *     "map": <__ff_imorted_forms_map> }
 *
 * Run:  wp eval-file tools/b3h_form_dump.php --allow-root
 */

global $wpdb;

$norm_gf_field = static function ($fl) {
    $choices = [];
    if (isset($fl->choices) && is_array($fl->choices)) {
        foreach ($fl->choices as $c) {
            $choices[] = is_array($c) ? (string) ($c['text'] ?? '') : (string) ($c->text ?? '');
        }
    }
    return [
        'type'        => (string) $fl->type,
        'label'       => trim(strip_tags((string) $fl->label)),
        // Hidden fields carry their identifying text in adminLabel; FF maps that
        // to admin_field_label, so the gate compares admin-side names there.
        'admin_label' => trim(strip_tags((string) ($fl->adminLabel ?? ''))),
        'required'    => !empty($fl->isRequired),
        'choices'     => $choices,
        'html'        => trim((string) ($fl->content ?? '')),
        'placeholder' => trim((string) ($fl->placeholder ?? '')),
    ];
};

$norm_ff_field = static function ($field) {
    $settings = is_array($field['settings'] ?? null) ? $field['settings'] : [];
    $choices = [];
    // The migrator stores option lists under advanced_options ({label,value,id});
    // hand-built forms in the builder UI use options. Read both, prefer advanced.
    $opts = $field['settings']['advanced_options'] ?? ($field['settings']['options'] ?? []);
    if (is_array($opts)) {
        foreach ($opts as $o) {
            $choices[] = trim(strip_tags((string) ($o['label'] ?? '')));
        }
    }
    $rules = $field['settings']['validation_rules'] ?? [];
    // Fluent Forms marks a required field by the presence of the rule and a
    // truthy value; both spellings are seen in the wild.
    $required = false;
    if (isset($rules['required'])) {
        $req = $rules['required'];
        $required = is_array($req) ? !empty($req['value']) : (bool) $req;
    }
    // A hidden field has no visible label; FF keeps the GF label as the admin
    // label, which is the honest counterpart for comparison.
    $label = $settings['label'] ?? '';
    if (($field['element'] ?? '') === 'input_hidden' && '' === trim((string) $label)) {
        $label = $settings['admin_field_label'] ?? '';
    }
    return [
        'type'            => (string) ($field['element'] ?? ''),
        'label'           => trim(strip_tags((string) $label)),
        'required'        => $required,
        'choices'         => $choices,
        'html'            => trim((string) ($settings['html_codes'] ?? '')),
        'placeholder'     => trim((string) ($field['attributes']['placeholder'] ?? '')),
        'input_type'      => (string) ($field['attributes']['type'] ?? ''),
        // null = key absent (FF would then apply its own default, time ON);
        // anything present is normalised to bool so '' counts as date-only.
        'is_time_enabled' => array_key_exists('is_time_enabled', $settings)
                                ? (bool) $settings['is_time_enabled']
                                : null,
    ];
};

$out = ['gf' => [], 'ff' => [], 'ff_notification_rows' => [], 'map' => get_option('__ff_imorted_forms_map')];

if (class_exists('GFAPI')) {
    foreach (GFAPI::get_forms(true, false) as $f) {
        $fields = [];
        foreach ((array) $f['fields'] as $fl) {
            $fields[] = $norm_gf_field($fl);
        }
        $notifs = [];
        foreach ((array) $f['notifications'] as $n) {
            $notifs[] = [
                'to'      => (string) ($n['to'] ?? ''),
                'subject' => (string) ($n['subject'] ?? ''),
                'event'   => (string) ($n['event'] ?? ''),
            ];
        }
        $out['gf'][(string) $f['id']] = [
            'title'         => (string) $f['title'],
            'active'        => !empty($f['is_active']),
            'fields'        => $fields,
            'notifications' => $notifs,
        ];
    }
}

$rows = $wpdb->get_results("SELECT id, title, form_fields, status FROM {$wpdb->prefix}fluentform_forms ORDER BY id");
foreach ($rows as $r) {
    $decoded = json_decode((string) $r->form_fields, true);
    $fields  = [];
    foreach ((array) ($decoded['fields'] ?? []) as $field) {
        if (!is_array($field)) {
            continue;
        }
        $fields[] = $norm_ff_field($field);
    }
    $out['ff'][(string) $r->id] = [
        'title'    => (string) $r->title,
        'status'   => (string) $r->status,
        'elements' => array_values(array_filter(array_map(
            static function ($f) { return is_array($f) ? ($f['element'] ?? null) : null; },
            (array) ($decoded['fields'] ?? [])
        ))),
        'fields'   => $fields,
    ];
    $out['ff_notification_rows'][(string) $r->id] = (int) $wpdb->get_var($wpdb->prepare(
        "SELECT COUNT(*) FROM {$wpdb->prefix}fluentform_form_meta WHERE form_id = %d AND meta_key = 'notifications'",
        (int) $r->id
    ));
}

echo json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
