<?php
/**
 * Gravity Forms -> Fluent Forms, with the stock migrator's two gaps repaired.
 *
 * The plugin's own migrator is used for everything it gets right, and its field
 * builder still produces the stored field structures, so the output stays valid
 * for the installed Fluent Forms version. Two repairs sit on top, both found by
 * diffing the result rather than by trusting the import:
 *
 *   phone   GravityFormsMigrator.php:220 maps GF's phone field to the element
 *           'phone', which is a Fluent Forms *Pro* element -- BaseMigrator.php:1398
 *           lists it in $proElements. On the free build getFluentClassicField()
 *           therefore returns nothing and getFields() drops the field silently
 *           (it only lands in $unSupportFields, which nobody reads here).
 *           Measured cost: "Request a Sample" lost Phone / WhatsApp; "Book a
 *           Factory Tour" lost it too. Retargeted to input_text with type=tel.
 *
 *   time    GravityFormsMigrator.php:227 maps it to 'input_date'. Fluent Forms
 *           has no input_time element at all (87 occurrences of input_date, zero
 *           of input_time), and its date element is literally titled "Time & Date"
 *           with is_time_enabled defaulting to true. So the stock mapping would
 *           leave the tour form with two date+time pickers, one of them labelled
 *           "Preferred Time". Sent to input_text so it stays a plain time, and the
 *           date field next to it is switched to a date-only picker.
 *
 * Reset-then-import so the result is deterministic: Fluent Forms does not reuse
 * form ids, so re-running a half-finished import would otherwise pile up copies.
 *
 * Run: wp eval-file tools/b3h_form_migrate.php --allow-root
 */

global $wpdb;

$SOURCE_IDS = ['2', '3', '4', '5', '6'];   // the site's forms; GF 1 is an empty inactive leftover
$DEMO_TITLES = ['Contact Form Demo', 'Subscription Form'];

$log = ['reset' => [], 'imported' => [], 'repairs' => [], 'unsupported' => []];

/* ---------------------------------------------------------------- reset ---- */

$map = get_option('__ff_imorted_forms_map');
$victims = [];
if (is_array($map)) {
    foreach ($map as $ffId => $info) {
        $victims[] = (int) $ffId;
    }
}
foreach ($wpdb->get_results("SELECT id, title FROM {$wpdb->prefix}fluentform_forms") as $r) {
    if (in_array((string) $r->title, $DEMO_TITLES, true)) {
        $victims[] = (int) $r->id;
    }
}
$victims = array_values(array_unique(array_filter($victims)));
foreach ($victims as $id) {
    $wpdb->delete("{$wpdb->prefix}fluentform_forms", ['id' => $id]);
    $wpdb->delete("{$wpdb->prefix}fluentform_form_meta", ['form_id' => $id]);
    $wpdb->delete("{$wpdb->prefix}fluentform_submissions", ['form_id' => $id]);
    $log['reset'][] = $id;
}
delete_option('__ff_imorted_forms_map');

/* ------------------------------------------------------------ migrator ---- */

$mig = new FluentForm\App\Services\Migrator\Classes\GravityFormsMigrator();
$ref = new ReflectionObject($mig);
$call = static function ($name) use ($ref, $mig) {
    $m = $ref->getMethod($name);
    $m->setAccessible(true);
    return $m;
};
$getForms    = $call('getForms');
$getFormId   = $call('getFormId');
$updateMetas = $call('updateMetas');

/**
 * The two repairs, applied to the Gravity Forms form array the builder reads.
 * Returning the form unchanged apart from field types keeps every other decision
 * (labels, choices, validation, ordering, notifications) with the plugin.
 */
$repair_source_types = static function ($form, &$note) {
    foreach ($form['fields'] as $i => $field) {
        $f = (array) $field;
        $type = (string) ($f['type'] ?? '');
        $label = trim(strip_tags((string) ($f['label'] ?? '')));
        if ('phone' === $type) {
            $f['type'] = 'text';
            $f['_sf_repair'] = 'phone';
            $form['fields'][$i] = (object) $f;
            $note[] = sprintf('phone -> input_text (GF field %s %s)', $f['id'] ?? '?', $label);
        } elseif ('time' === $type) {
            $f['type'] = 'text';
            $f['_sf_repair'] = 'time';
            $form['fields'][$i] = (object) $f;
            $note[] = sprintf('time -> input_text (GF field %s %s)', $f['id'] ?? '?', $label);
        }
    }
    return $form;
};

/** Walk the container in place; Fluent Forms stores a flat list of field rows. */
$walk = static function (&$fields, callable $fn) {
    foreach ($fields as &$row) {
        if (isset($row['element'])) {
            $fn($row);
        } else {
            foreach ($row as &$sub) {
                $fn($sub);
            }
            unset($sub);
        }
    }
    unset($row);
};

$insertedForms = [];
$refs = [];
$forms = $getForms->invoke($mig);

foreach ($forms as $formItem) {
    $gfId = (string) $getFormId->invoke($mig, $formItem);
    if (!in_array($gfId, $SOURCE_IDS, true)) {
        continue;
    }

    $notes = [];
    $prepared = $repair_source_types($formItem, $notes);

    $fields = $mig->getFields($prepared);
    if (!$fields) {
        $log['unsupported'][] = $gfId;
        continue;
    }

    // Map GF field id -> the repair that applies, so the produced structures can
    // be adjusted by identity rather than by guessing at positions.
    $repair = [];
    foreach ($prepared['fields'] as $f) {
        $f = (array) $f;
        if (!empty($f['_sf_repair'])) {
            $repair[(string) $f['id']] = $f['_sf_repair'];
        }
    }

    $walk($fields['fields'], static function (&$field) use ($repair, &$notes) {
        $idx = (string) ($field['index'] ?? '');
        if (!isset($repair[$idx])) {
            // Dates: Fluent Forms' own default is a combined "Time & Date" picker.
            // The tour form pairs this with a separate Preferred Time, so a
            // date-only picker is the honest rendering.
            if ('input_date' === ($field['element'] ?? '') &&
                !empty($field['settings']['is_time_enabled'])) {
                $field['settings']['is_time_enabled'] = false;
                $notes[] = 'date field switched to date-only (is_time_enabled=false)';
            }
            return;
        }
        if ('phone' === $repair[$idx]) {
            $field['attributes']['type'] = 'tel';
            if ('' === (string) ($field['attributes']['placeholder'] ?? '')) {
                $field['attributes']['placeholder'] = 'e.g. +86 138 0000 0000';
            }
            $notes[] = 'phone field carries type=tel';
        } else {
            if ('' === (string) ($field['attributes']['placeholder'] ?? '')) {
                $field['attributes']['placeholder'] = 'e.g. 10:00 (GMT+8)';
            }
            $notes[] = 'time field carries a time placeholder';
        }
    });

    $nameMethod = $ref->getMethod('getFormName');
    $nameMethod->setAccessible(true);
    $formName = (string) $nameMethod->invoke($mig, $formItem);

    $form = [
        'title'               => $formName,
        'form_fields'         => json_encode($fields),
        'status'              => 'published',
        'has_payment'         => 0,
        'type'                => 'form',
        'created_by'          => 0,
        'conditions'          => '',
        'appearance_settings' => '',
    ];

    list($insertedForms, $ffId) = $mig->insertForm($form, $insertedForms, $formItem);
    $updateMetas->invoke($mig, $mig->getFormMetas($formItem), $ffId);

    $refs[$ffId] = ['imported_form_id' => (int) $gfId, 'form_type' => $mig->key];

    $leafCount = 0;
    foreach ($fields['fields'] as $row) {
        $leafCount += isset($row['element']) ? 1 : count((array) $row);
    }

    $log['imported'][] = [
        'gf'      => $gfId,
        'gf_name' => $formName,
        'ff'      => $ffId,
        'fields'  => $leafCount,
    ];
    $log['repairs'][$gfId] = $notes;
}

if ($refs) {
    update_option('__ff_imorted_forms_map', $refs, 'no');
}

echo json_encode($log, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
