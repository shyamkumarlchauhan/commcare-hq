DROP VIEW IF EXISTS thr_report_monthly CASCADE;
CREATE VIEW thr_report_monthly AS
SELECT
"awc_location_months"."awc_id" AS "awc_id",
"awc_location_months"."awc_name" AS "awc_name",
"awc_location_months"."awc_site_code" AS "awc_site_code",
"awc_location_months"."supervisor_id" AS "supervisor_id",
"awc_location_months"."supervisor_name" AS "supervisor_name",
"awc_location_months"."supervisor_site_code" AS "supervisor_site_code",
"awc_location_months"."block_id" AS "block_id",
"awc_location_months"."block_name" AS "block_name",
"awc_location_months"."block_site_code" AS "block_site_code",
"awc_location_months"."district_id" AS "district_id",
"awc_location_months"."district_name" AS "district_name",
"awc_location_months"."district_site_code" AS "district_site_code",
"awc_location_months"."state_id" AS "state_id",
"awc_location_months"."state_name" AS "state_name",
"awc_location_months"."state_site_code" AS "state_site_code",
"awc_location_months"."block_map_location_name" AS "block_map_location_name",
"awc_location_months"."district_map_location_name" AS "district_map_location_name",
"awc_location_months"."state_map_location_name" AS "state_map_location_name",
"awc_location_months"."aww_name" AS "aww_name",
"awc_location_months"."contact_phone_number" AS "contact_phone_number",
"awc_location_months"."aggregation_level" AS "aggregation_level",
COALESCE(agg_awc.thr_distribution_image_count,0) as thr_distribution_image_count,
agg_awc.is_launched,
agg_awc.month as month,
COALESCE(agg_awc.thr_rations_21_plus_distributed_child,0) + COALESCE(agg_awc.num_mother_thr_21_days,0) as thr_given_21_days,
COALESCE(agg_awc.thr_eligible_child,0) + COALESCE (agg_awc.num_mother_thr_eligible,0) as total_thr_candidates
FROM "public"."awc_location_months_local" "awc_location_months"
LEFT join agg_awc on (
        ("awc_location_months"."month" = "agg_awc"."month") AND
        ("agg_awc"."state_id" = "awc_location_months"."state_id") AND
        ("agg_awc"."district_id" = "awc_location_months"."district_id") AND
        ("agg_awc"."block_id" = "awc_location_months"."block_id") AND
        ("agg_awc"."supervisor_id" = "awc_location_months"."supervisor_id") AND
        ("agg_awc"."aggregation_level" = "awc_location_months"."aggregation_level") AND
        ("agg_awc"."awc_id" = "awc_location_months"."awc_id")
        );
